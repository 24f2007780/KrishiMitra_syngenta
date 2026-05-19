"""
M7 Engagement Model — Behavioral Click Prediction
Syngenta IITM Hackathon 2026

═══════════════════════════════════════════════════════════════════
LAYER 2: BEHAVIORAL ENGAGEMENT CLASSIFIER
═══════════════════════════════════════════════════════════════════

Target: clicked_status (binary)
  - Strongest intent signal in the dataset
  - ~5% base rate (hard prediction problem)
  - Meaningful action (farmer actively engaged)

Features: ONLY real behavioral/demographic signals
  - NO synthetic pest_risk / weather_anomaly (those are agronomic, not behavioral)
  - NO np.random.uniform() fabrication
  - District CTR, device type, farm size, recency, seasonality

Evaluation: Temporal split (train: Oct–Feb, test: Mar–Apr)
  - No random split — prevents chronological leakage

Output: engagement_model.pkl
  - Serialized pipeline + population priors for cold-start
═══════════════════════════════════════════════════════════════════
"""

import argparse
import pickle
import logging
import math
import json
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, log_loss, average_precision_score
from sklearn.preprocessing import MinMaxScaler
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False
    print("xgboost not installed. Run: pip install xgboost")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "recency_penalty",
    "grower_farm_size",
    "grower_age",
    "product_scan_flag",
    "offline_attended_flag",
    "district_ctr",
    "month",
    "week_of_season",
    "seasonal_demand",
    "crop_wheat",
    "crop_mustard",
    "crop_chickpea",
    "crop_potato",
    "device_smartphone",
    "device_keypad",
]


def parse_crop(cal):
    try:
        cal = json.loads(cal) if isinstance(cal, str) else {}
        return str(cal.get("crop", "wheat")).lower()
    except Exception:
        return "wheat"


def train(data_dir: str, output_path: str):
    if not XGB_AVAILABLE:
        raise RuntimeError("xgboost is required. pip install xgboost")

    data_dir = Path(data_dir)
    logger.info("Loading CSVs from %s", data_dir)

    growers_df = pd.read_csv(data_dir / "growers.csv")
    msg_path = data_dir / "whatsapp_campaign.csv"
    if not msg_path.exists():
        msg_path = data_dir / "whatsapp_message_log.csv"
    msg_df = pd.read_csv(msg_path)

    msg_df["message_sent_date"] = pd.to_datetime(msg_df["message_sent_date"])

    # ── Target: clicked_status ONLY ────────────────────────────────────
    logger.info("Target: clicked_status (base rate: %.4f)", msg_df["clicked_status"].mean())

    # ── Merge grower demographics ──────────────────────────────────────
    df = msg_df.merge(
        growers_df[["grower_id", "district", "state", "device_type",
                    "grower_age", "grower_farm_size", "grower_crop_calendar",
                    "product_scan", "offline_campaign_attended"]],
        on="grower_id", how="inner"
    )

    # ── Compute district CTR (leave-one-out to prevent leakage) ────────
    # Use global mean for districts with < 5 messages
    district_counts = df.groupby("district")["clicked_status"].agg(["sum", "count"])
    global_ctr = float(df["clicked_status"].mean())
    district_ctr_map = {}
    for dist, row in district_counts.iterrows():
        if row["count"] >= 5:
            district_ctr_map[dist] = row["sum"] / row["count"]
        else:
            district_ctr_map[dist] = global_ctr

    # ── Compute crop-level CTR (population prior for cold-start) ───────
    df["crop"] = df["grower_crop_calendar"].apply(parse_crop)
    crop_ctr_map = df.groupby("crop")["clicked_status"].mean().to_dict()

    # ── Feature engineering (NO synthetic features) ────────────────────
    # Recency: days since last message to this grower BEFORE current message
    df = df.sort_values(["grower_id", "message_sent_date"])
    df["prev_msg_date"] = df.groupby("grower_id")["message_sent_date"].shift(1)
    df["days_since_prev"] = (df["message_sent_date"] - df["prev_msg_date"]).dt.days.fillna(999)
    half_life = 7 / math.log(2)
    df["recency_penalty"] = np.exp(-df["days_since_prev"] / half_life).clip(0, 1)

    # Demographics
    df["grower_farm_size"] = df["grower_farm_size"].fillna(df["grower_farm_size"].median())
    df["grower_age"] = df["grower_age"].fillna(df["grower_age"].median())

    # Behavioral flags
    df["product_scan_flag"] = df["product_scan"].astype(int)
    df["offline_attended_flag"] = df["offline_campaign_attended"].astype(int)

    # District CTR
    df["district_ctr"] = df["district"].map(district_ctr_map).fillna(global_ctr)

    # Temporal
    df["month"] = df["message_sent_date"].dt.month.astype(float)
    rabi_start = pd.Timestamp("2025-11-01")
    df["days_since_rabi"] = (df["message_sent_date"] - rabi_start).dt.days.clip(0)
    df["week_of_season"] = (df["days_since_rabi"] // 7).clip(0, 52).astype(float)

    demand_curve = {
        11: 0.8, 12: 0.95, 1: 0.9, 2: 0.7, 3: 0.4,
        4: 0.2, 5: 0.1, 6: 0.2, 7: 0.5, 8: 0.6, 9: 0.4, 10: 0.5,
    }
    df["seasonal_demand"] = df["month"].map(demand_curve).fillna(0.5)

    # Crop dummies
    for c in ["wheat", "mustard", "chickpea", "potato"]:
        df[f"crop_{c}"] = (df["crop"] == c).astype(int)

    # Device dummies
    df["device_type"] = df["device_type"].fillna("unknown")
    for d in ["smartphone", "keypad"]:
        df[f"device_{d}"] = (df["device_type"] == d).astype(int)

    # ── Temporal split (NOT random) ────────────────────────────────────
    # Train: Oct 2025 – Feb 2026, Test: Mar – Apr 2026
    split_date = pd.Timestamp("2026-03-01")
    train_mask = df["message_sent_date"] < split_date
    test_mask = df["message_sent_date"] >= split_date

    train_df = df[train_mask].copy()
    test_df = df[test_mask].copy()

    logger.info("Temporal split: Train=%d (before %s), Test=%d (after)",
                len(train_df), split_date.date(), len(test_df))
    logger.info("Train CTR: %.4f, Test CTR: %.4f",
                train_df["clicked_status"].mean(), test_df["clicked_status"].mean())

    X_train = train_df[FEATURE_COLS].values
    y_train = train_df["clicked_status"].values.astype(int)
    X_test = test_df[FEATURE_COLS].values
    y_test = test_df["clicked_status"].values.astype(int)

    # ── Build pipeline ─────────────────────────────────────────────────
    logger.info("Training XGBoost engagement classifier...")

    # Handle class imbalance with scale_pos_weight
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    scale_pos_weight = neg_count / pos_count if pos_count > 0 else 1.0

    base_clf = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        objective="binary:logistic",
        random_state=42,
        eval_metric="logloss",
    )

    calibrated_clf = CalibratedClassifierCV(estimator=base_clf, method="isotonic", cv=3)

    pipeline = Pipeline([
        ("scaler", MinMaxScaler()),
        ("model", calibrated_clf),
    ])

    pipeline.fit(X_train, y_train)

    # ── Evaluate ───────────────────────────────────────────────────────
    train_probs = pipeline.predict_proba(X_train)[:, 1]
    test_probs = pipeline.predict_proba(X_test)[:, 1]

    train_auc = roc_auc_score(y_train, train_probs)
    test_auc = roc_auc_score(y_test, test_probs)
    test_ap = average_precision_score(y_test, test_probs)
    test_loss = log_loss(y_test, test_probs)

    logger.info("Train ROC-AUC: %.4f", train_auc)
    logger.info("Test  ROC-AUC: %.4f  (temporal holdout)", test_auc)
    logger.info("Test  Avg Precision: %.4f", test_ap)
    logger.info("Test  Log Loss: %.4f", test_loss)
    logger.info("Test  Prob range: [%.4f, %.4f]", test_probs.min(), test_probs.max())

    # Feature importances
    fitted_calibrator = pipeline.named_steps["model"]
    importances = np.mean(
        [est.estimator.feature_importances_ for est in fitted_calibrator.calibrated_classifiers_],
        axis=0
    )
    importances_dict = dict(zip(FEATURE_COLS, [float(v) for v in importances]))
    logger.info("Feature importances: %s", importances_dict)

    # ── Population priors for cold-start ───────────────────────────────
    # These are used when a farmer has no history
    logger.info("Computing population priors for cold-start...")
    population_priors = {
        "global_ctr": global_ctr,
        "district_ctr_map": district_ctr_map,
        "crop_ctr_map": crop_ctr_map,
        "device_ctr": df.groupby("device_type")["clicked_status"].mean().to_dict(),
        "median_farm_size": float(df["grower_farm_size"].median()),
        "median_age": float(df["grower_age"].median()),
    }
    logger.info("  Global CTR: %.4f", global_ctr)
    logger.info("  District CTRs: %d districts", len(district_ctr_map))
    logger.info("  Crop CTRs: %s", crop_ctr_map)

    # ── Grower profile maps for inference ──────────────────────────────
    grower_geo_map = growers_df[["grower_id", "state", "district"]].set_index("grower_id").to_dict(orient="index")
    grower_profile_map = growers_df[["grower_id", "product_scan", "offline_campaign_attended"]].set_index("grower_id").to_dict(orient="index")

    # ── Serialize ──────────────────────────────────────────────────────
    model_payload = {
        "pipeline": pipeline,
        "grower_geo_map": grower_geo_map,
        "grower_profile_map": grower_profile_map,
        "district_ctr_map": district_ctr_map,
        "global_ctr": global_ctr,
        "population_priors": population_priors,
        "min_prob": float(test_probs.min()),
        "max_prob": float(test_probs.max()),
        "feature_importances": importances_dict,
        "metrics": {
            "train_auc": train_auc,
            "test_auc": test_auc,
            "test_ap": test_ap,
            "test_loss": test_loss,
        },
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        pickle.dump(model_payload, f)
    logger.info("Engagement model saved → %s", output_path)
    logger.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train M7 engagement classifier (clicked_status)")
    parser.add_argument("--data-dir", required=True, help="Directory containing CSV files")
    parser.add_argument("--output", default="ml/engagement_model.pkl")
    args = parser.parse_args()
    train(args.data_dir, args.output)
