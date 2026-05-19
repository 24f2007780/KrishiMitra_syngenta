"""
M7 Urgency Scorer — Model Quality Evaluation
=============================================
Answers: Is the model actually good? How do we know?

The dataset has NO explicit "urgency" labels. So the training script
CONSTRUCTS a proxy target from observed behavioral signals:

    y = 1 if (clicked_whatsapp OR opened_message OR purchased_within_7d OR scanned_product)

This script:
1. Reconstructs that target from raw data
2. Evaluates the model's predictions against it
3. Checks calibration (does predicted probability match actual conversion rate?)
4. Validates that urgency scores correlate with real-world engagement
5. Runs a "lift analysis" — do high-urgency growers actually convert more?
"""

import sys
import math
from pathlib import Path
from datetime import date

import numpy as np
import pandas as pd
from sklearn.metrics import (
    roc_auc_score, log_loss, precision_recall_curve,
    average_precision_score, classification_report
)

sys.path.insert(0, ".")
from app.scorer import _load_model, _build_feature_vector, score_ml, score_formula, clip
from app.models import FarmerContext, CropType

DATA_DIR = Path("../Dataset/Syngenta_IITM_Hackathon_2026_dataset")

print("=" * 70)
print("M7 URGENCY MODEL — QUALITY EVALUATION")
print("=" * 70)
print()

# ── 1. Load raw data and reconstruct target ────────────────────────────────────
print("[1] LOADING DATA & RECONSTRUCTING TARGET VARIABLE")
print("-" * 50)

growers_df = pd.read_csv(DATA_DIR / "growers.csv")
msg_df = pd.read_csv(DATA_DIR / "whatsapp_campaign.csv")
retailers_df = pd.read_csv(DATA_DIR / "retailers.csv")
pos_df = pd.read_csv(DATA_DIR / "retailer_pos.csv")

msg_df["message_sent_date"] = pd.to_datetime(msg_df["message_sent_date"])
pos_df["transaction_date"] = pd.to_datetime(pos_df["transaction_date"])

print(f"    Growers: {len(growers_df)}")
print(f"    WhatsApp messages: {len(msg_df)}")
print(f"    POS transactions: {len(pos_df)}")
print()

# Reconstruct purchased_7d (same logic as train.py)
ret_geo = retailers_df[["retailer_id", "tehsil"]]
pos_geo = pos_df.merge(ret_geo, on="retailer_id", how="inner")
pos_grouped = pos_geo.groupby(["tehsil", "sku_name", "transaction_date"])["sku_qty"].sum().reset_index()

pos_lookup = set()
for _, row in pos_grouped.iterrows():
    pos_lookup.add((row["tehsil"], row["sku_name"].lower(), row["transaction_date"]))

grower_geo = growers_df[["grower_id", "tehsil"]].set_index("grower_id")

purchased_7d_list = []
for _, row in msg_df.iterrows():
    g_id = row["grower_id"]
    sent_date = row["message_sent_date"]
    prod = row["campaign_product"].lower()
    has_purchased = 0
    if g_id in grower_geo.index:
        teh = grower_geo.loc[g_id, "tehsil"]
        for offset in range(0, 8):
            check_date = sent_date + pd.Timedelta(days=offset)
            if (teh, prod, check_date) in pos_lookup:
                has_purchased = 1
                break
    purchased_7d_list.append(has_purchased)

msg_df["purchased_7d"] = purchased_7d_list

# Build unified target
msg_df["y"] = (
    msg_df["clicked_status"].astype(bool) |
    msg_df["opened_status"].astype(bool) |
    (msg_df["purchased_7d"] > 0)
).astype(int)

grower_target = msg_df.groupby("grower_id")["y"].max().reset_index()
scanners = set(growers_df[growers_df["product_scan"] == True]["grower_id"])
grower_target.loc[grower_target["grower_id"].isin(scanners), "y"] = 1

print(f"    Target variable breakdown:")
print(f"      - Clicked WhatsApp link: {msg_df['clicked_status'].sum()}")
print(f"      - Opened message: {msg_df['opened_status'].sum()}")
print(f"      - Purchased within 7d: {sum(msg_df['purchased_7d'] > 0)}")
print(f"      - Product scanners: {len(scanners)}")
print(f"      - Growers with y=1: {grower_target['y'].sum()} / {len(grower_target)} ({grower_target['y'].mean()*100:.1f}%)")
print()

# ── 2. Score all growers with the ML model ─────────────────────────────────────
print("[2] SCORING ALL GROWERS WITH ML MODEL")
print("-" * 50)

payload = _load_model()
assert payload is not None, "Model not loaded!"

# Build contexts for all growers in the message dataset
results = []
for _, grow in growers_df.iterrows():
    gid = grow["grower_id"]
    if gid not in grower_target["grower_id"].values:
        continue

    # Parse crop from calendar
    import json
    try:
        cal = json.loads(grow["grower_crop_calendar"]) if isinstance(grow["grower_crop_calendar"], str) else {}
        crop_str = str(cal.get("crop", "wheat")).lower()
    except Exception:
        crop_str = "wheat"

    crop_map = {"wheat": CropType.wheat, "mustard": CropType.mustard, "chickpea": CropType.chickpea, "potato": CropType.potato}
    crop = crop_map.get(crop_str, CropType.wheat)

    # Get last message date for this grower
    grower_msgs = msg_df[msg_df["grower_id"] == gid]
    last_msg = grower_msgs["message_sent_date"].max() if len(grower_msgs) > 0 else None
    last_msg_date = last_msg.date() if pd.notna(last_msg) else None

    # Get farm size (handle NaN)
    farm_size = grow.get("grower_farm_size")
    if pd.isna(farm_size):
        farm_size = None
    
    grower_age = None
    if pd.notna(grow.get("grower_age")):
        grower_age = int(grow["grower_age"])

    device = grow.get("device_type", "unknown")
    if pd.isna(device):
        device = "unknown"

    ctx = FarmerContext(
        grower_id=gid,
        crop=crop,
        pest_risk=0.5,  # will be overridden by feature vector
        weather_anomaly=0.5,
        crop_vulnerability=0.5,
        last_message_date=last_msg_date,
        scoring_date=date(2026, 4, 5),  # end of dataset period
        grower_farm_size=farm_size,
        grower_age=grower_age,
        device_type=device,
    )

    ml_score, ml_comps = score_ml(ctx)
    if ml_score is not None:
        prob = ml_comps["calibrated_conversion_probability"]
        results.append({
            "grower_id": gid,
            "urgency_score": round(ml_score, 2),
            "probability": prob,
        })

results_df = pd.DataFrame(results)
results_df = results_df.merge(grower_target, on="grower_id", how="inner")

print(f"    Scored {len(results_df)} growers")
print(f"    Urgency score range: [{results_df['urgency_score'].min():.2f}, {results_df['urgency_score'].max():.2f}]")
print(f"    Mean urgency: {results_df['urgency_score'].mean():.3f}")
print()

# ── 3. Classification Metrics ──────────────────────────────────────────────────
print("[3] CLASSIFICATION METRICS (probability vs actual conversion)")
print("-" * 50)

y_true = results_df["y"].values
y_prob = results_df["probability"].values
y_score = results_df["urgency_score"].values

auc = roc_auc_score(y_true, y_prob)
ap = average_precision_score(y_true, y_prob)
loss = log_loss(y_true, y_prob)

print(f"    ROC-AUC:              {auc:.4f}")
print(f"    Average Precision:    {ap:.4f}")
print(f"    Log Loss:             {loss:.4f}")
print()

# Also check AUC using the urgency_score directly
auc_urgency = roc_auc_score(y_true, y_score)
print(f"    ROC-AUC (urgency):    {auc_urgency:.4f}  (using scaled urgency score)")
print()

# ── 4. Calibration Check ──────────────────────────────────────────────────────
print("[4] CALIBRATION CHECK (predicted prob vs actual conversion rate)")
print("-" * 50)

# Bin by predicted probability
results_df["prob_bin"] = pd.cut(results_df["probability"], bins=5)
cal_table = results_df.groupby("prob_bin", observed=True).agg(
    count=("y", "count"),
    actual_rate=("y", "mean"),
    predicted_prob=("probability", "mean"),
).reset_index()

print(f"    {'Prob Bin':<25} {'Count':<8} {'Actual Rate':<14} {'Predicted':<12} {'Gap'}")
print(f"    {'-'*25} {'-'*8} {'-'*14} {'-'*12} {'-'*8}")
for _, row in cal_table.iterrows():
    gap = abs(row["actual_rate"] - row["predicted_prob"])
    print(f"    {str(row['prob_bin']):<25} {int(row['count']):<8} {row['actual_rate']:.3f}{'':>8} {row['predicted_prob']:.3f}{'':>6} {gap:.3f}")
print()

# ── 5. Lift Analysis — Do high-urgency growers actually convert more? ──────────
print("[5] LIFT ANALYSIS (does urgency score predict real engagement?)")
print("-" * 50)

# Split into urgency quartiles
results_df["urgency_quartile"] = pd.qcut(results_df["urgency_score"], q=4, labels=["Q1 (Low)", "Q2", "Q3", "Q4 (High)"])

lift_table = results_df.groupby("urgency_quartile", observed=True).agg(
    count=("y", "count"),
    conversion_rate=("y", "mean"),
    avg_urgency=("urgency_score", "mean"),
).reset_index()

baseline_rate = results_df["y"].mean()
lift_table["lift"] = lift_table["conversion_rate"] / baseline_rate

print(f"    Baseline conversion rate: {baseline_rate:.3f}")
print()
print(f"    {'Quartile':<12} {'Count':<8} {'Conv Rate':<12} {'Avg Urgency':<14} {'Lift'}")
print(f"    {'-'*12} {'-'*8} {'-'*12} {'-'*14} {'-'*8}")
for _, row in lift_table.iterrows():
    print(f"    {row['urgency_quartile']:<12} {int(row['count']):<8} {row['conversion_rate']:.3f}{'':>6} {row['avg_urgency']:.3f}{'':>8} {row['lift']:.2f}x")
print()

# ── 6. Monotonicity Check ─────────────────────────────────────────────────────
print("[6] MONOTONICITY CHECK (higher urgency → higher conversion?)")
print("-" * 50)

deciles = pd.qcut(results_df["urgency_score"], q=10, duplicates="drop")
mono_table = results_df.groupby(deciles, observed=True)["y"].mean()
rates = mono_table.values
monotonic_violations = sum(1 for i in range(len(rates)-1) if rates[i] > rates[i+1])
print(f"    Decile conversion rates: {[f'{r:.3f}' for r in rates]}")
print(f"    Monotonicity violations: {monotonic_violations} / {len(rates)-1}")
print(f"    Mostly monotonic: {'YES' if monotonic_violations <= 2 else 'NO'}")
print()

# ── 7. Feature Importance Sanity Check ─────────────────────────────────────────
print("[7] FEATURE IMPORTANCE (does the model rely on sensible features?)")
print("-" * 50)

importances = payload["feature_importances"]
sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)
print(f"    Top features driving the model:")
for feat, imp in sorted_imp[:8]:
    bar = "█" * int(imp * 50)
    print(f"      {feat:<25} {imp:.4f}  {bar}")
print()

# ── 8. Verdict ─────────────────────────────────────────────────────────────────
print("=" * 70)
print("VERDICT")
print("=" * 70)
print()
print(f"  ROC-AUC = {auc:.4f}  (>0.70 = acceptable, >0.75 = good, >0.80 = strong)")
print(f"  Lift Q4/Q1 = {lift_table.iloc[-1]['lift']:.2f}x / {lift_table.iloc[0]['lift']:.2f}x")
print()

if auc >= 0.70:
    print("  ✓ The model has meaningful predictive power.")
else:
    print("  ✗ The model is weak — barely better than random.")

if lift_table.iloc[-1]["conversion_rate"] > lift_table.iloc[0]["conversion_rate"]:
    print("  ✓ High-urgency growers DO convert more than low-urgency ones.")
else:
    print("  ✗ Urgency score does NOT correlate with actual conversions.")

if monotonic_violations <= 2:
    print("  ✓ Score is mostly monotonic — higher score = higher engagement.")
else:
    print("  ✗ Score has non-monotonic behavior (unreliable ranking).")

print()
print("  NOTE: There are no explicit 'urgency' labels in the dataset.")
print("  The model learns to predict ENGAGEMENT LIKELIHOOD as a proxy:")
print("    y=1 if grower clicked, opened, purchased, or scanned product.")
print("  This is a valid proxy because urgency should correlate with")
print("  the probability that a message leads to farmer action.")
print()
print("  The urgency score is the model's calibrated engagement probability,")
print("  rescaled to [0,1] for interpretability. It answers:")
print("  'How likely is this farmer to act if we message them NOW?'")
print("=" * 70)
