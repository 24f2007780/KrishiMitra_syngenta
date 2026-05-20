"""
M7 Intelligence Engine — New Farmer Entry Demo
Syngenta IITM Hackathon 2026

Demonstrates the 3-stage cold-start flow:
  Stage 1: Build FarmerContext from input
  Stage 2: Agronomic urgency scoring (works immediately)
  Stage 3: Behavioral ML refinement (cold-start with population priors)
"""
import sys
import json
sys.path.insert(0, ".")

from datetime import date, timedelta
from app.models import FarmerContext, CropType, DeviceType
from app.scorer import compute_urgency, score_urgency, score_engagement

print("=" * 70)
print("M7 INTELLIGENCE ENGINE — NEW FARMER ENTRY FLOW")
print("=" * 70)
print()

# ── Stage 1: Build FarmerContext ───────────────────────────────────────────────
print("┌─────────────────────────────────────────────────────────────────┐")
print("│  STAGE 1: Build FarmerContext                                   │")
print("└─────────────────────────────────────────────────────────────────┘")
print()

# Simulating input from an external system
raw_input = {
    "grower_id": "F1021",
    "crop_type": "wheat",
    "district": "Nashik",
    "pest_risk": 0.82,
    "weather_anomaly": 0.71,
    "crop_vulnerability": 0.66,
    "hours_since_last_message": 48,
}
print(f"  Input: {json.dumps(raw_input, indent=4)}")
print()

# Convert hours to date for recency
scoring_date = date(2026, 2, 10)
hours = raw_input["hours_since_last_message"]
last_msg_date = scoring_date - timedelta(hours=hours) if hours else None

ctx = FarmerContext(
    grower_id=raw_input["grower_id"],
    crop=CropType.wheat,
    pest_risk=raw_input["pest_risk"],
    weather_anomaly=raw_input["weather_anomaly"],
    crop_vulnerability=raw_input["crop_vulnerability"],
    last_message_date=last_msg_date,
    scoring_date=scoring_date,
    device_type=DeviceType.smartphone,
)
print(f"  → FarmerContext built: grower_id={ctx.grower_id}, crop={ctx.crop.value}")
print(f"    pest_risk={ctx.pest_risk}, weather={ctx.weather_anomaly}, vuln={ctx.crop_vulnerability}")
print(f"    last_message={ctx.last_message_date}, scoring_date={ctx.scoring_date}")
print()

# ── Stage 2: Agronomic Urgency ─────────────────────────────────────────────────
print("┌─────────────────────────────────────────────────────────────────┐")
print("│  STAGE 2: Agronomic Urgency Scoring (Rule Engine)               │")
print("│  Works immediately — no historical data needed                  │")
print("└─────────────────────────────────────────────────────────────────┘")
print()

urgency_score, urgency_comps = score_urgency(ctx)
print(f"  Formula: 0.40×{ctx.pest_risk} + 0.30×{ctx.weather_anomaly} + 0.20×{ctx.crop_vulnerability} + 0.10×(1 − recency)")
print(f"  Recency penalty: {urgency_comps['recency_penalty_raw']:.4f}")
print()
print(f"  Breakdown:")
print(f"    Pest risk term:     0.40 × {ctx.pest_risk:.2f} = {urgency_comps['pest_risk_term']:.4f}")
print(f"    Weather term:       0.30 × {ctx.weather_anomaly:.2f} = {urgency_comps['weather_anomaly_term']:.4f}")
print(f"    Vulnerability term: 0.20 × {ctx.crop_vulnerability:.2f} = {urgency_comps['crop_vulnerability_term']:.4f}")
print(f"    Recency term:       0.10 × (1 − {urgency_comps['recency_penalty_raw']:.4f}) = {urgency_comps['recency_term']:.4f}")
print()
print(f"  ► URGENCY SCORE = {urgency_score:.4f}")
print(f"  ► Top factors: {urgency_comps['top_factors']}")
print()

# ── Stage 3: Behavioral ML Refinement ──────────────────────────────────────────
print("┌─────────────────────────────────────────────────────────────────┐")
print("│  STAGE 3: Behavioral ML Refinement                              │")
print("│  New farmer → cold-start with population priors                 │")
print("└─────────────────────────────────────────────────────────────────┘")
print()

engagement_score, eng_comps = score_engagement(ctx)
is_cold_start = eng_comps.get("cold_start", False)
model_used = eng_comps.get("model_used", False)

if is_cold_start:
    print("  ⚠ COLD START: Farmer not in training population")
    print("  → Using population priors (district CTR, crop CTR, device CTR)")
    priors = eng_comps.get("priors_used", {})
    for k, v in priors.items():
        print(f"    {k}: {v}")
elif model_used:
    print("  ✓ Known farmer: Full ML engagement prediction")
    print(f"    Calibrated probability: {eng_comps.get('calibrated_probability')}")
else:
    print("  ○ Heuristic fallback (no model loaded)")

print()
print(f"  ► ENGAGEMENT SCORE = {engagement_score:.4f}")
print(f"  ► Factors: {eng_comps['top_factors']}")
print()

# ── Full Pipeline Result ───────────────────────────────────────────────────────
print("┌─────────────────────────────────────────────────────────────────┐")
print("│  FINAL: Combined Priority + Delivery Intelligence               │")
print("└─────────────────────────────────────────────────────────────────┘")
print()

result = compute_urgency(ctx)

print(f"  ┌────────────────────────────────────────────┐")
print(f"  │  Agronomic Urgency:    {result.urgency_score:.2f}                │")
print(f"  │  Engagement Score:     {result.engagement_score:.2f}                │")
print(f"  │  Priority Score:       {result.priority_score:.2f}                │")
print(f"  │  Recommended Channel:  {result.recommended_channel.value:<18} │")
print(f"  │  Suppress:             {str(result.suppress):<18} │")
print(f"  └────────────────────────────────────────────┘")
print()

if result.suppress:
    print(f"  ⚠ SUPPRESSED: {result.suppress_reason}")
else:
    print(f"  ✓ ACTIVE: Message this farmer via {result.recommended_channel.value}")

print()
print(f"  Top decision factors:")
for f in result.top_factors:
    print(f"    → {f}")

print()
print(f"  Model version: {result.model_version}")
print()

# ── Demonstrate cold-start vs known farmer ─────────────────────────────────────
print("=" * 70)
print("COMPARISON: New Farmer vs Known Farmer")
print("=" * 70)
print()

# Known farmer (exists in training data)
ctx_known = FarmerContext(
    grower_id="G_0001",  # exists in growers.csv
    crop=CropType.wheat,
    pest_risk=0.82,
    weather_anomaly=0.71,
    crop_vulnerability=0.66,
    last_message_date=scoring_date - timedelta(days=2),
    scoring_date=scoring_date,
    device_type=DeviceType.smartphone,
)
result_known = compute_urgency(ctx_known)

# New farmer (not in training data)
ctx_new = FarmerContext(
    grower_id="BRAND_NEW_F9999",
    crop=CropType.wheat,
    pest_risk=0.82,
    weather_anomaly=0.71,
    crop_vulnerability=0.66,
    last_message_date=scoring_date - timedelta(days=2),
    scoring_date=scoring_date,
    device_type=DeviceType.smartphone,
)
result_new = compute_urgency(ctx_new)

print(f"  {'Metric':<25} {'Known Farmer':<18} {'New Farmer'}")
print(f"  {'-'*25} {'-'*18} {'-'*18}")
print(f"  {'Urgency Score':<25} {result_known.urgency_score:<18.2f} {result_new.urgency_score:.2f}")
print(f"  {'Engagement Score':<25} {result_known.engagement_score:<18.2f} {result_new.engagement_score:.2f}")
print(f"  {'Priority Score':<25} {result_known.priority_score:<18.2f} {result_new.priority_score:.2f}")
print(f"  {'Channel':<25} {result_known.recommended_channel.value:<18} {result_new.recommended_channel.value}")
print(f"  {'Suppress':<25} {str(result_known.suppress):<18} {str(result_new.suppress)}")
print(f"  {'Cold Start?':<25} {str(result_known.engagement_components.get('cold_start', False)):<18} {str(result_new.engagement_components.get('cold_start', False))}")
print()
print("  Key insight: Both farmers get the SAME urgency score (same conditions).")
print("  Engagement differs based on available history vs population priors.")
print("  System never breaks — it degrades gracefully.")
print()
print("=" * 70)
print("SYSTEM READY FOR PRODUCTION")
print("=" * 70)
