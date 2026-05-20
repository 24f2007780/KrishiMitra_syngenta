"""
M9 Campaign Receptivity — ML Training Pipeline
Syngenta IITM Hackathon 2026

Trains:
1. Farmer segmentation (from engagement history)
2. Receptivity classifier (XGBoost on clicked_status)
3. Precomputes segment-level format engagement rates

Target: clicked_status (strongest intent signal)
Split: Temporal (train Oct–Feb, test Mar–Apr)
"""

import argparse
import pickle
import logging
import json
import math
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, log_loss
from sklearn.preprocessing import MinMaxScaler
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV

try:
    import xgboost as xgb
except ImportError:
    xgb = None
    print("xgboost not installed")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_crop(cal):
    try:
        cal = json.loads(cal) if isinstance(cal, str) else {}
        return str(cal.get("crop", "unknown")).lower()
    except:
        return "unknown"


def train(data_dir: str, output_path: str):
    data_dir = Path(data_dir)
    logger.info("Loading data from %s", data_dir)

    growers_df = pd.read_csv(data_dir / "growers.csv")
    msg_df = pd.read_csv(data_dir / "whatsapp_campaign.csv")

    msg_df["message_sent_date"] = pd.to_datetime(msg_df["message_sent_date"])
    growers_df["crop"] = growers_df["grower_crop_calendar"].apply(parse_crop)

    # ── 1. Farmer Segmentation ─────────────────────────────────────────
    logger.info("Computing farmer segments from engagement history...")

    grower_stats = msg_df.groupby("grower_id").agg(
        total_msgs=("id", "count"),
        opens=("opened_status", "sum"),
        clicks=("clicked_status", "sum"),
    ).reset_index()

    grower_stats["open_rate"] = grower_stats["opens"] / grower_stats["total_msgs"]
    grower_stats["click_rate"] = grower_stats["clicks"] / grower_stats["total_msgs"]

    def assign_segment(row):
        if row["click_rate"] > 0.08:
            return "digital_active"
        elif row["open_rate"] > 0.3:
            return "digital_passive"
        else:
            return "offline_only"

    grower_stats["segment"] = grower_stats.apply(assign_segment, axis=1)

    grower_segments = {}
    for _, row in grower_stats.iterrows():
        grower_segments[row["grower_id"]] = {
            "segment": row["segment"],
            "confidence": 0.85 if row["total_msgs"] >= 3 else 0.60,
            "open_rate": round(row["open_rate"], 4),
            "click_rate": round(row["click_rate"], 4),
        }

    seg_counts = grower_stats["segment"].value_counts()
    logger.info("  Segments: %s", seg_counts.to_dict())

    # ── 2. Feature Engineering ─────────────────────────────────────────
    logger.info("Engineering features for receptivity model...")

    df = msg_df.merge(
        growers_df[["grower_id", "district", "device_type", "grower_age",
                    "grower_farm_size", "crop", "product_scan",
                    "offline_campaign_attended"]],
        on="grower_id", how="inner"
    )

    # Segment encoding
    seg_map = {"digital_active": 3, "digital_passive": 2, "offline_only": 1}
    df["segment_val"] = df["grower_id"].map(
        lambda g: seg_map.get(grower_segments.get(g, {}).get("segment", "offline_only"), 1)
    )

    # Device encoding
    df["device_val"] = df["device_type"].map({"smartphone": 2, "keypad": 1}).fillna(0)

    # Temporal
    df["month"] = df["message_sent_date"].dt.month.astype(float)
    df["day_of_week"] = df["message_sent_date"].dt.weekday.astype(float)

    # Historical engagement (rolling — use all prior messages for this grower)
    df = df.sort_values(["grower_id", "message_sent_date"])
    df["cum_opens"] = df.groupby("grower_id")["opened_status"].cumsum().shift(1).fillna(0)
    df["cum_msgs"] = df.groupby("grower_id").cumcount()
    df["hist_open_rate"] = (df["cum_opens"] / df["cum_msgs"].clip(1)).fillna(0.23)

    df["cum_clicks"] = df.groupby("grower_id")["clicked_status"].cumsum().shift(1).fillna(0)
    df["hist_click_rate"] = (df["cum_clicks"] / df["cum_msgs"].clip(1)).fillna(0.05)

    # Messages in last 30 days (approximate)
    df["msgs_30d"] = df.groupby("grower_id").cumcount().clip(0, 10).astype(float)

    # Profile features
    df["farm_size"] = df["grower_farm_size"].fillna(2.5)
    df["age"] = df["grower_age"].fillna(42.0)
    df["scanned"] = df["product_scan"].astype(float)
    df["attended"] = df["offline_campaign_attended"].astype(float)

    # District CTR
    global_ctr = float(df["clicked_status"].mean())
    district_ctr_map = df.groupby("district")["clicked_status"].mean().to_dict()
    df["district_ctr"] = df["district"].map(district_ctr_map).fillna(global_ctr)

    # Crop CTR
    crop_ctr_map = df.groupby("crop")["clicked_status"].mean().to_dict()
    df["crop_ctr"] = df["crop"].map(crop_ctr_map).fillna(global_ctr)

    FEATURE_COLS = [
        "segment_val", "device_val", "month", "day_of_week",
        "hist_open_rate", "hist_click_rate", "msgs_30d",
        "farm_size", "age", "scanned", "attended",
        "district_ctr", "crop_ctr",
    ]

    # ── 3. Temporal Split & Training ───────────────────────────────────
    split_date = pd.Timestamp("2026-03-01")
    train_mask = df["message_sent_date"] < split_date
    test_mask = df["message_sent_date"] >= split_date

    X_train = df.loc[train_mask, FEATURE_COLS].values
    y_train = df.loc[train_mask, "clicked_status"].values.astype(int)
    X_test = df.loc[test_mask, FEATURE_COLS].values
    y_test = df.loc[test_mask, "clicked_status"].values.astype(int)

    logger.info("Train: %d, Test: %d", len(X_train), len(X_test))
    logger.info("Train CTR: %.4f, Test CTR: %.4f", y_train.mean(), y_test.mean())

    if xgb is None:
        logger.warning("XGBoost not available — saving without pipeline")
        pipeline = None
        test_auc = 0.0
        min_prob, max_prob = 0.01, 0.15
    else:
        neg = (y_train == 0).sum()
        pos = (y_train == 1).sum()
        spw = neg / pos if pos > 0 else 1.0

        base_clf = xgb.XGBClassifier(
            n_estimators=150, max_depth=3, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            scale_pos_weight=spw, random_state=42, eval_metric="logloss",
        )
        calibrated = CalibratedClassifierCV(estimator=base_clf, method="isotonic", cv=3)
        pipeline = Pipeline([("scaler", MinMaxScaler()), ("model", calibrated)])
        pipeline.fit(X_train, y_train)

        test_probs = pipeline.predict_proba(X_test)[:, 1]
        test_auc = roc_auc_score(y_test, test_probs) if len(set(y_test)) > 1 else 0.5
        min_prob = float(test_probs.min())
        max_prob = float(test_probs.max())
        logger.info("Test ROC-AUC: %.4f", test_auc)

    # ── 4. Save Model Payload ──────────────────────────────────────────
    model_payload = {
        "pipeline": pipeline,
        "grower_segments": grower_segments,
        "district_ctr_map": district_ctr_map,
        "crop_ctr_map": crop_ctr_map,
        "global_ctr": global_ctr,
        "min_prob": min_prob,
        "max_prob": max_prob,
        "metrics": {"test_auc": test_auc},
        "segment_distribution": seg_counts.to_dict(),
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(model_payload, f)
    logger.info("Receptivity model saved → %s", output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output", default="ml/receptivity_model.pkl")
    args = parser.parse_args()
    train(args.data_dir, args.output)
