"""
M7 Intelligence Engine — Learn Agronomic Urgency Coefficients
Syngenta IITM Hackathon 2026

═══════════════════════════════════════════════════════════════════
REPLACES HAND-TUNED WEIGHTS WITH DATA-CALIBRATED COEFFICIENTS
═══════════════════════════════════════════════════════════════════

Approach:
  - Keep the interpretable linear formula structure
  - Learn coefficients via LogisticRegression on real outcomes
  - Target: clicked_status | product_scan (meaningful engagement)
  - Features: pest_risk, weather_anomaly, crop_vulnerability, recency

Result:
  - Same explainable formula
  - Coefficients backed by data instead of intuition
  - Removes "hackathon heuristic" smell
  - Preserves determinism and interpretability

Output: ml/urgency_weights.json
"""

import argparse
import json
import math
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import MinMaxScaler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_vulnerability(cal_json):
    """Derive crop vulnerability from growth stage calendar."""
    HIGH_RISK_STAGES = {"flowering", "heading", "tuber_initiation", "pod_fill"}
    try:
        cal = json.loads(cal_json) if isinstance(cal_json, str) else {}
        stages = set(str(v).lower() for v in cal.values())
        return 1.0 if stages & HIGH_RISK_STAGES else 0.4
    except Exception:
        return 0.5


def train(data_dir: str, output_path: str):
    data_dir = Path(data_dir)
    logger.info("Loading data from %s", data_dir)

    growers_df = pd.read_csv(data_dir / "growers.csv")
    msg_df = pd.read_csv(data_dir / "whatsapp_campaign.csv")
    retailers_df = pd.read_csv(data_dir / "retailers.csv")
    pos_df = pd.read_csv(data_dir / "retailer_pos.csv")

    msg_df["message_sent_date"] = pd.to_datetime(msg_df["message_sent_date"])
    pos_df["transaction_date"] = pd.to_datetime(pos_df["transaction_date"])

    # ── Build target: clicked OR product_scan (meaningful engagement) ──
    # Merge grower profiles
    df = msg_df.merge(
        growers_df[["grower_id", "state", "district", "grower_crop_calendar",
                    "product_scan"]],
        on="grower_id", how="inner"
    )

    # Target: clicked_status OR product_scan (real intent signals)
    df["y"] = (df["clicked_status"].astype(bool) | df["product_scan"].astype(bool)).astype(int)
    logger.info("Target (clicked | product_scan): %.4f base rate", df["y"].mean())

    # ── Engineer agronomic features from REAL data ─────────────────────
    # Crop vulnerability from growth calendar
    df["crop_vulnerability"] = df["grower_crop_calendar"].apply(parse_vulnerability)

    # Weather anomaly proxy: state-level POS velocity deviation
    # High POS activity in a district = farmers buying protection = weather stress
    ret_geo = retailers_df[["retailer_id", "state"]].drop_duplicates()
    pos_state = pos_df.merge(ret_geo, on="retailer_id", how="inner")
    state_pos_rate = pos_state.groupby("state")["sku_qty"].sum()
    state_pos_norm = (state_pos_rate - state_pos_rate.min()) / (state_pos_rate.max() - state_pos_rate.min())
    state_weather_proxy = state_pos_norm.to_dict()
    df["weather_anomaly"] = df["state"].map(state_weather_proxy).fillna(0.5)

    # Pest risk proxy: product-specific POS spikes (fungicide/insecticide demand)
    # Higher demand for crop protection = higher pest pressure
    pest_products = ["kavach", "actara", "score", "topik"]
    pest_pos = pos_df[pos_df["sku_name"].str.lower().str.contains("|".join(pest_products), na=False)]
    pest_by_date = pest_pos.groupby(pos_df["transaction_date"].dt.isocalendar().week)["sku_qty"].sum()
    # Normalize per-message: map message week to pest intensity
    df["msg_week"] = df["message_sent_date"].dt.isocalendar().week.astype(int)
    week_pest = (pest_by_date - pest_by_date.min()) / (pest_by_date.max() - pest_by_date.min())
    df["pest_risk"] = df["msg_week"].map(week_pest.to_dict()).fillna(0.5)

    # Recency penalty
    df = df.sort_values(["grower_id", "message_sent_date"])
    df["prev_msg_date"] = df.groupby("grower_id")["message_sent_date"].shift(1)
    df["days_since_prev"] = (df["message_sent_date"] - df["prev_msg_date"]).dt.days.fillna(999)
    half_life = 7 / math.log(2)
    df["recency_penalty"] = np.exp(-df["days_since_prev"] / half_life).clip(0, 1)
    df["communication_window"] = 1.0 - df["recency_penalty"]

    # ── Feature matrix (same 4 features as the formula) ────────────────
    feature_cols = ["pest_risk", "weather_anomaly", "crop_vulnerability", "communication_window"]
    X = df[feature_cols].values
    y = df["y"].values

    # Temporal split
    split_date = pd.Timestamp("2026-03-01")
    train_mask = df["message_sent_date"] < split_date
    test_mask = df["message_sent_date"] >= split_date

    X_train, y_train = X[train_mask], y[train_mask]
    X_test, y_test = X[test_mask], y[test_mask]

    logger.info("Train: %d samples, Test: %d samples", len(X_train), len(X_test))
    logger.info("Train positive rate: %.4f, Test positive rate: %.4f",
                y_train.mean(), y_test.mean())

    # ── Fit LogisticRegression (interpretable linear model) ────────────
    # No regularization penalty to get true coefficient magnitudes
    lr = LogisticRegression(
        penalty=None,
        max_iter=1000,
        random_state=42,
    )
    lr.fit(X_train, y_train)

    # ── Extract and normalize coefficients to sum to 1.0 ───────────────
    raw_coefs = lr.coef_[0]
    # Use absolute values (all should be positive for urgency)
    abs_coefs = np.abs(raw_coefs)
    normalized_weights = abs_coefs / abs_coefs.sum()

    logger.info("Raw LR coefficients: %s", dict(zip(feature_cols, raw_coefs)))
    logger.info("Normalized weights: %s", dict(zip(feature_cols, normalized_weights)))

    # ── Evaluate ───────────────────────────────────────────────────────
    train_probs = lr.predict_proba(X_train)[:, 1]
    test_probs = lr.predict_proba(X_test)[:, 1]

    train_auc = roc_auc_score(y_train, train_probs)
    test_auc = roc_auc_score(y_test, test_probs)

    logger.info("Train ROC-AUC: %.4f", train_auc)
    logger.info("Test  ROC-AUC: %.4f (temporal holdout)", test_auc)

    # ── Compare with hand-tuned weights ────────────────────────────────
    hand_weights = np.array([0.40, 0.30, 0.20, 0.10])
    hand_scores_test = X_test @ hand_weights
    hand_auc = roc_auc_score(y_test, hand_scores_test)
    logger.info("Hand-tuned weights AUC: %.4f", hand_auc)
    logger.info("Learned weights AUC:    %.4f", test_auc)
    logger.info("Improvement: %+.4f", test_auc - hand_auc)

    # ── Save learned weights ───────────────────────────────────────────
    output = {
        "learned_weights": {
            "pest_risk": round(float(normalized_weights[0]), 4),
            "weather_anomaly": round(float(normalized_weights[1]), 4),
            "crop_vulnerability": round(float(normalized_weights[2]), 4),
            "communication_window": round(float(normalized_weights[3]), 4),
        },
        "raw_coefficients": dict(zip(feature_cols, [round(float(c), 4) for c in raw_coefs])),
        "intercept": round(float(lr.intercept_[0]), 4),
        "hand_tuned_weights": {
            "pest_risk": 0.40,
            "weather_anomaly": 0.30,
            "crop_vulnerability": 0.20,
            "communication_window": 0.10,
        },
        "validation_metrics": {
            "train_auc": round(train_auc, 4),
            "test_auc_temporal": round(test_auc, 4),
            "hand_tuned_auc": round(hand_auc, 4),
            "improvement_over_hand_tuned": round(test_auc - hand_auc, 4),
            "train_samples": int(len(X_train)),
            "test_samples": int(len(X_test)),
            "train_positive_rate": round(float(y_train.mean()), 4),
            "test_positive_rate": round(float(y_test.mean()), 4),
        },
        "methodology": {
            "model": "LogisticRegression (no penalty)",
            "target": "clicked_status | product_scan",
            "features": feature_cols,
            "split": "temporal (train: Oct-Feb, test: Mar-Apr)",
            "normalization": "absolute coefficients normalized to sum=1.0",
        },
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    logger.info("Saved learned weights → %s", output_path)
    print()
    print("=" * 60)
    print("LEARNED URGENCY WEIGHTS")
    print("=" * 60)
    print(f"  pest_risk:            {normalized_weights[0]:.4f}  (was 0.40)")
    print(f"  weather_anomaly:      {normalized_weights[1]:.4f}  (was 0.30)")
    print(f"  crop_vulnerability:   {normalized_weights[2]:.4f}  (was 0.20)")
    print(f"  communication_window: {normalized_weights[3]:.4f}  (was 0.10)")
    print()
    print(f"  Test AUC (learned):    {test_auc:.4f}")
    print(f"  Test AUC (hand-tuned): {hand_auc:.4f}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Learn urgency formula coefficients from data")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--output", default="ml/urgency_weights.json")
    args = parser.parse_args()
    train(args.data_dir, args.output)
