"""
M7 Urgency Scorer — Hybrid Intelligence Engine
Syngenta IITM Hackathon 2026

═══════════════════════════════════════════════════════════════════
ARCHITECTURE: Domain-Informed Urgency Intelligence Engine
           with Adaptive ML Enrichment
═══════════════════════════════════════════════════════════════════

Layer 1 — Agronomic Rule Engine (PRIMARY)
    Deterministic, explainable urgency from domain knowledge.
    urgency = 0.40×pest_risk + 0.30×weather_anomaly
            + 0.20×crop_vulnerability + 0.10×(1 − recency_penalty)

Layer 2 — Behavioral ML Layer (ENRICHMENT)
    XGBoost classifier trained on clicked_status (real engagement signal).
    Predicts: "Will this farmer respond to outreach?"

Layer 3 — Delivery Intelligence (FUSION)
    Combines urgency + engagement + fatigue suppression.
    Outputs: intervention_priority, recommended_channel, suppress flag.

═══════════════════════════════════════════════════════════════════
"""

import os
import math
import logging
import pickle
from datetime import date
from typing import Optional, Tuple
import numpy as np

from shared.models import (
    FarmerContext, UrgencyResponse, ChannelRecommendation, DeviceType, CropType
)

logger = logging.getLogger(__name__)

class _UrgencyContext:
    def __init__(self, shared_ctx):
        if hasattr(shared_ctx, 'profile'):
            self.grower_id = shared_ctx.profile.grower_id
            crop_val = shared_ctx.profile.crops[0] if shared_ctx.profile.crops else "wheat"
            try:
                self.crop = CropType(crop_val.lower())
            except ValueError:
                self.crop = CropType.wheat
            
            # Direct float assignment with fallback
            if hasattr(shared_ctx.signals, 'pest_risk') and isinstance(shared_ctx.signals.pest_risk, (int, float)):
                self.pest_risk = float(shared_ctx.signals.pest_risk)
            elif hasattr(shared_ctx.signals, 'pest_risk_level') and shared_ctx.signals.pest_risk_level:
                pest_risk_map = {"high": 0.8, "medium": 0.5, "low": 0.2}
                self.pest_risk = pest_risk_map.get(str(shared_ctx.signals.pest_risk_level).lower(), 0.2)
            else:
                self.pest_risk = 0.2

            if hasattr(shared_ctx.signals, 'weather_anomaly') and isinstance(shared_ctx.signals.weather_anomaly, (int, float)):
                self.weather_anomaly = float(shared_ctx.signals.weather_anomaly)
            else:
                self.weather_anomaly = 0.8 if getattr(shared_ctx.signals, 'weather_anomaly_flag', False) else 0.2

            if hasattr(shared_ctx.crop_stage, 'crop_vulnerability') and isinstance(shared_ctx.crop_stage.crop_vulnerability, (int, float)):
                self.crop_vulnerability = float(shared_ctx.crop_stage.crop_vulnerability)
            elif hasattr(shared_ctx.crop_stage, 'vulnerability') and shared_ctx.crop_stage.vulnerability:
                vuln_map = {"high": 0.8, "medium": 0.5, "low": 0.2}
                self.crop_vulnerability = vuln_map.get(str(shared_ctx.crop_stage.vulnerability).lower(), 0.2)
            else:
                self.crop_vulnerability = 0.2
            
            self.last_message_date = None
            if shared_ctx.profile.last_message_sent_at:
                try:
                    from datetime import datetime
                    self.last_message_date = datetime.strptime(
                        shared_ctx.profile.last_message_sent_at.split("T")[0], "%Y-%m-%d"
                    ).date()
                except ValueError:
                    pass
            
            self.scoring_date = date.today()
            if shared_ctx.assembled_at:
                try:
                    from datetime import datetime
                    self.scoring_date = datetime.strptime(
                        shared_ctx.assembled_at.split("T")[0], "%Y-%m-%d"
                    ).date()
                except ValueError:
                    pass
            
            self.grower_farm_size = shared_ctx.profile.grower_farm_size
            self.grower_age = shared_ctx.profile.grower_age
            
            try:
                self.device_type = DeviceType(shared_ctx.profile.device_type.lower())
            except ValueError:
                self.device_type = DeviceType.unknown
            
            self.previously_clicked_whatsapp = shared_ctx.profile.messages_opened_last_30d > 0
            self.whatsapp_enabled = shared_ctx.profile.whatsapp_enabled
            self.connectivity = shared_ctx.profile.connectivity
            self.messages_received_last_30d = shared_ctx.profile.messages_received_last_30d
            self.messages_opened_last_30d = shared_ctx.profile.messages_opened_last_30d
        else:
            self.grower_id = getattr(shared_ctx, 'grower_id', None)
            self.crop = getattr(shared_ctx, 'crop', None)
            self.pest_risk = getattr(shared_ctx, 'pest_risk', 0.5)
            self.weather_anomaly = getattr(shared_ctx, 'weather_anomaly', 0.5)
            self.crop_vulnerability = getattr(shared_ctx, 'crop_vulnerability', 0.5)
            self.last_message_date = getattr(shared_ctx, 'last_message_date', None)
            self.scoring_date = getattr(shared_ctx, 'scoring_date', date.today())
            self.grower_farm_size = getattr(shared_ctx, 'grower_farm_size', 2.0)
            self.grower_age = getattr(shared_ctx, 'grower_age', 35)
            dt = getattr(shared_ctx, 'device_type', DeviceType.unknown)
            if isinstance(dt, str):
                try:
                    self.device_type = DeviceType(dt.lower())
                except ValueError:
                    self.device_type = DeviceType.unknown
            elif dt is None:
                self.device_type = DeviceType.unknown
            else:
                self.device_type = dt
            self.previously_clicked_whatsapp = getattr(shared_ctx, 'previously_clicked_whatsapp', None)
            self.whatsapp_enabled = getattr(shared_ctx, 'whatsapp_enabled', True)
            self.connectivity = getattr(shared_ctx, 'connectivity', '4G')
            self.messages_received_last_30d = getattr(shared_ctx, 'messages_received_last_30d', 0)
            self.messages_opened_last_30d = getattr(shared_ctx, 'messages_opened_last_30d', 0)

# ── Configuration ──────────────────────────────────────────────────────────────
HARD_SUPPRESS_DAYS = 3
SOFT_SUPPRESS_DAYS = 7
SOFT_THRESHOLD = 0.45  # intervention_priority below this gets soft-suppressed

# Weights for combining urgency + engagement into priority
URGENCY_WEIGHT = 0.70
ENGAGEMENT_WEIGHT = 0.30

MODEL_PATH = os.getenv("ENGAGEMENT_MODEL_PATH", "ml/engagement_model.pkl")
WEIGHTS_PATH = os.getenv("URGENCY_WEIGHTS_PATH", "ml/urgency_weights.json")
MODEL_VERSION = "m7-hybrid-v2"

# Intervention cost model (relative units)
CHANNEL_COSTS = {
    "whatsapp": 0.05,
    "sms": 0.10,
    "voice_call": 0.50,
    "field_visit": 1.00,
    "suppress": 0.00,
}
INTERVENTION_BENEFIT = 1.0  # normalized benefit of successful engagement

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


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1: AGRONOMIC RULE ENGINE
# ══════════════════════════════════════════════════════════════════════════════

# Default weights (hand-tuned baseline)
_DEFAULT_WEIGHTS = {
    "pest_risk": 0.40,
    "weather_anomaly": 0.30,
    "crop_vulnerability": 0.20,
    "communication_window": 0.10,
}

_learned_weights_cache = None


def _load_urgency_weights() -> dict:
    """Load learned coefficients from JSON. Falls back to defaults."""
    global _learned_weights_cache
    if _learned_weights_cache is not None:
        return _learned_weights_cache
    try:
        import json
        with open(WEIGHTS_PATH, "r") as f:
            data = json.load(f)
        _learned_weights_cache = data["learned_weights"]
        logger.info("Loaded learned urgency weights from %s", WEIGHTS_PATH)
        return _learned_weights_cache
    except FileNotFoundError:
        logger.info("No learned weights at %s — using defaults.", WEIGHTS_PATH)
        _learned_weights_cache = _DEFAULT_WEIGHTS
        return _learned_weights_cache
    except Exception as exc:
        logger.warning("Failed to load weights: %s — using defaults.", exc)
        _learned_weights_cache = _DEFAULT_WEIGHTS
        return _learned_weights_cache

def compute_recency_penalty(
    last_message_date: Optional[date],
    scoring_date: date,
    soft_window: int = SOFT_SUPPRESS_DAYS,
) -> float:
    """
    Exponential decay penalty in [0, 1].
    penalty = exp(-days / half_life), half_life = soft_window / ln(2).
    At soft_window days, penalty ≈ 0.5.
    """
    if last_message_date is None:
        return 0.0
    days_since = (scoring_date - last_message_date).days
    if days_since < 0:
        days_since = 0
    half_life = soft_window / math.log(2)
    return math.exp(-days_since / half_life)


def score_urgency(ctx: FarmerContext) -> Tuple[float, dict]:
    """
    Layer 1: Agronomic urgency score with data-calibrated coefficients.

    Formula structure (interpretable linear combination):
        urgency = w1×pest_risk + w2×weather_anomaly
                + w3×crop_vulnerability + w4×(1 − recency_penalty)

    Weights are learned from LogisticRegression on real engagement outcomes,
    preserving explainability while removing hand-tuning arbitrariness.

    Important nuance: The learned coefficients optimize INTERVENTION
    RESPONSIVENESS, not biological risk causality. communication_window
    dominates because recently-messaged farmers engage less — behaviorally
    true, but does not mean timing equals pest severity.
    """
    ctx = _UrgencyContext(ctx)
    weights = _load_urgency_weights()
    recency_penalty = compute_recency_penalty(ctx.last_message_date, ctx.scoring_date)

    w_pest = weights["pest_risk"]
    w_weather = weights["weather_anomaly"]
    w_vuln = weights["crop_vulnerability"]
    w_comm = weights["communication_window"]

    pest_term = w_pest * ctx.pest_risk
    weather_term = w_weather * ctx.weather_anomaly
    vuln_term = w_vuln * ctx.crop_vulnerability
    recency_term = w_comm * (1.0 - recency_penalty)

    raw_score = pest_term + weather_term + vuln_term + recency_term
    raw_score = _clip(raw_score, 0.0, 1.0)

    # Build explainability factors (sorted by contribution)
    factor_contributions = [
        ("High Pest Outbreak Risk", pest_term, ctx.pest_risk),
        ("Severe Weather Deviation", weather_term, ctx.weather_anomaly),
        ("Critical Crop Stage Vulnerability", vuln_term, ctx.crop_vulnerability),
        ("Communication Window Available", recency_term, 1.0 - recency_penalty),
    ]
    factor_contributions.sort(key=lambda x: x[1], reverse=True)

    top_factors = [f[0] for f in factor_contributions if f[1] > 0.03][:3]
    if not top_factors:
        top_factors = ["Resilient local conditions"]

    components = {
        "pest_risk_term": round(pest_term, 4),
        "weather_anomaly_term": round(weather_term, 4),
        "crop_vulnerability_term": round(vuln_term, 4),
        "recency_term": round(recency_term, 4),
        "recency_penalty_raw": round(recency_penalty, 4),
        "weights_source": "learned" if weights != _DEFAULT_WEIGHTS else "default",
        "weights_used": {k: round(v, 4) for k, v in weights.items()},
        "top_factors": top_factors,
    }

    return raw_score, components


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2: BEHAVIORAL ML LAYER
# ══════════════════════════════════════════════════════════════════════════════

_model_cache = None


def _load_model():
    """Lazy-load the engagement model."""
    global _model_cache
    if _model_cache is not None:
        return _model_cache
    try:
        with open(MODEL_PATH, "rb") as f:
            _model_cache = pickle.load(f)
        logger.info("Loaded engagement model from %s", MODEL_PATH)
        return _model_cache
    except FileNotFoundError:
        logger.info("Engagement model not found at %s — using heuristic fallback.", MODEL_PATH)
        return None
    except Exception as exc:
        logger.error("Failed to load engagement model: %s", exc)
        return None


def _build_engagement_features(ctx: FarmerContext, payload: dict) -> np.ndarray:
    """
    Build feature vector for engagement prediction.
    Uses ONLY real behavioral/demographic signals — no synthetic agronomic features.
    """
    recency_penalty = compute_recency_penalty(ctx.last_message_date, ctx.scoring_date)

    # Grower profile lookups
    grower_geo = payload["grower_geo_map"].get(ctx.grower_id, {})
    district = grower_geo.get("district", "unknown")

    grower_profile = payload["grower_profile_map"].get(ctx.grower_id, {})
    product_scan_flag = int(grower_profile.get("product_scan", False))
    offline_attended_flag = int(grower_profile.get("offline_campaign_attended", False))

    district_ctr = payload["district_ctr_map"].get(district, payload["global_ctr"])

    # Temporal features
    month = float(ctx.scoring_date.month)
    rabi_year = ctx.scoring_date.year if ctx.scoring_date.month >= 11 else ctx.scoring_date.year - 1
    rabi_start = date(rabi_year, 11, 1)
    days_since_rabi = (ctx.scoring_date - rabi_start).days
    week_of_season = float(_clip(days_since_rabi // 7, 0, 52))

    demand_curve = {
        11: 0.8, 12: 0.95, 1: 0.9, 2: 0.7, 3: 0.4,
        4: 0.2, 5: 0.1, 6: 0.2, 7: 0.5, 8: 0.6, 9: 0.4, 10: 0.5,
    }
    seasonal_demand = demand_curve.get(int(month), 0.5)

    # Crop & device dummies
    crop_onehot = {c: 0 for c in ["wheat", "mustard", "chickpea", "potato"]}
    if ctx.crop.value in crop_onehot:
        crop_onehot[ctx.crop.value] = 1

    device_onehot = {d: 0 for d in ["smartphone", "keypad"]}
    if ctx.device_type.value in device_onehot:
        device_onehot[ctx.device_type.value] = 1

    features = [
        recency_penalty,
        ctx.grower_farm_size if ctx.grower_farm_size is not None else 2.0,
        float(ctx.grower_age) if ctx.grower_age is not None else 42.0,
        product_scan_flag,
        offline_attended_flag,
        district_ctr,
        month,
        week_of_season,
        seasonal_demand,
        crop_onehot["wheat"],
        crop_onehot["mustard"],
        crop_onehot["chickpea"],
        crop_onehot["potato"],
        device_onehot["smartphone"],
        device_onehot["keypad"],
    ]

    return np.array(features, dtype=np.float32).reshape(1, -1)


def _is_known_grower(ctx: FarmerContext, payload: dict) -> bool:
    """Check if grower exists in the training population."""
    return ctx.grower_id in payload.get("grower_profile_map", {})


def _cold_start_engagement(ctx: FarmerContext, payload: dict) -> Tuple[float, dict]:
    """
    Cold-start strategy for new farmers with no behavioral history.

    Uses population priors:
      - District average CTR
      - Crop average response rate
      - Device-level engagement baseline

    This guarantees the system works immediately for new entries
    without requiring any historical data.
    """
    priors = payload.get("population_priors", {})
    global_ctr = priors.get("global_ctr", 0.05)

    # District prior
    grower_geo = payload["grower_geo_map"].get(ctx.grower_id, {})
    district = grower_geo.get("district", "unknown")
    district_ctr = priors.get("district_ctr_map", {}).get(district, global_ctr)

    # Crop prior
    crop_ctr = priors.get("crop_ctr_map", {}).get(ctx.crop.value, global_ctr)

    # Device prior
    device_ctr = priors.get("device_ctr", {}).get(ctx.device_type.value, global_ctr)

    # Weighted blend of priors
    prior_prob = 0.50 * district_ctr + 0.30 * crop_ctr + 0.20 * device_ctr

    # Scale to [0, 1] using same bounds as ML model
    min_prob = payload.get("min_prob", 0.01)
    max_prob = payload.get("max_prob", 0.20)
    engagement = (prior_prob - min_prob) / (max_prob - min_prob)
    engagement = _clip(engagement, 0.0, 1.0)

    factors = []
    if district_ctr > global_ctr * 1.2:
        factors.append(f"High-engagement district ({district})")
    if device_ctr > global_ctr:
        factors.append("Device type with above-average engagement")
    if crop_ctr > global_ctr:
        factors.append(f"Responsive crop segment ({ctx.crop.value})")
    if not factors:
        factors = ["Population baseline (new farmer — no history)"]

    components = {
        "calibrated_probability": round(prior_prob, 4),
        "engagement_scaled": round(engagement, 4),
        "top_factors": factors,
        "model_used": False,
        "cold_start": True,
        "priors_used": {
            "district_ctr": round(district_ctr, 4),
            "crop_ctr": round(crop_ctr, 4),
            "device_ctr": round(device_ctr, 4),
        },
    }
    return engagement, components


def score_engagement(ctx: FarmerContext) -> Tuple[float, dict]:
    """
    Layer 2: Behavioral engagement prediction.

    Flow:
      1. If ML model available AND grower has history → full ML prediction
      2. If ML model available BUT grower is new → cold-start with population priors
      3. If no model at all → heuristic fallback

    Predicts: "Will this farmer click/respond if we message them now?"
    Trained on clicked_status (real behavioral signal, ~5% base rate).
    """
    ctx = _UrgencyContext(ctx)
    payload = _load_model()

    if payload is None:
        # No model at all — pure heuristic
        engagement, components = _engagement_heuristic(ctx)
    elif not _is_known_grower(ctx, payload):
        # New farmer — use population priors (cold-start strategy)
        engagement, components = _cold_start_engagement(ctx, payload)
    else:
        # Known grower — full ML prediction
        fv = _build_engagement_features(ctx, payload)
        pipeline = payload["pipeline"]
        prob = float(pipeline.predict_proba(fv)[0][1])

        # Engagement score = calibrated probability, scaled to [0, 1]
        min_prob = payload.get("min_prob", 0.01)
        max_prob = payload.get("max_prob", 0.20)
        engagement = (prob - min_prob) / (max_prob - min_prob)
        engagement = _clip(engagement, 0.0, 1.0)

        # Explainability from feature importances
        importances = payload.get("feature_importances", {})
        human_names = {
            "product_scan_flag": "Active product scanner (high intent)",
            "offline_attended_flag": "Attended offline campaigns",
            "district_ctr": "High-engagement district",
            "seasonal_demand": "Peak seasonal demand period",
            "recency_penalty": "Recent communication (lower response)",
            "device_smartphone": "Smartphone user (higher digital engagement)",
            "grower_farm_size": "Larger farm (commercial orientation)",
        }

        contributions = []
        feat_names = FEATURE_COLS
        for i, feat in enumerate(feat_names):
            imp = importances.get(feat, 0.02)
            val = float(fv[0, i])
            contributions.append((human_names.get(feat, feat), val * imp))

        top_eng_factors = sorted(contributions, key=lambda x: x[1], reverse=True)[:3]
        top_eng_factors = [f[0] for f in top_eng_factors if f[1] > 0.005]
        if not top_eng_factors:
            top_eng_factors = ["Baseline engagement profile"]

        components = {
            "calibrated_probability": round(prob, 4),
            "engagement_scaled": round(engagement, 4),
            "top_factors": top_eng_factors,
            "model_used": True,
            "cold_start": False,
        }

    # Adjust based on messages history
    if ctx.messages_received_last_30d > 0:
        open_rate = ctx.messages_opened_last_30d / ctx.messages_received_last_30d
        engagement = 0.5 * engagement + 0.5 * open_rate
        engagement = _clip(engagement, 0.0, 1.0)
        components["engagement_scaled"] = round(engagement, 4)
        if open_rate >= 0.5:
            components["top_factors"] = ["High historical message open rate"] + [f for f in components["top_factors"] if f != "Baseline engagement profile"]
        elif open_rate == 0.0:
            components["top_factors"] = ["Zero message opens (low responsiveness)"] + [f for f in components["top_factors"] if f != "Baseline engagement profile"]
        components["top_factors"] = components["top_factors"][:3]

    return engagement, components


def _engagement_heuristic(ctx: FarmerContext) -> Tuple[float, dict]:
    """
    Simple heuristic engagement estimate when ML model is unavailable.
    Based on observable behavioral signals.
    """
    score = 0.3  # baseline

    # Smartphone users engage more with digital channels
    if ctx.device_type.value == "smartphone":
        score += 0.15

    # Previously clicked = strong engagement signal
    if ctx.previously_clicked_whatsapp:
        score += 0.25

    # Recency: recently messaged farmers have lower marginal response
    recency = compute_recency_penalty(ctx.last_message_date, ctx.scoring_date)
    score -= 0.15 * recency

    # Farm size proxy for commercial orientation
    if ctx.grower_farm_size and ctx.grower_farm_size > 5:
        score += 0.10

    score = _clip(score, 0.0, 1.0)

    factors = []
    if ctx.device_type.value == "smartphone":
        factors.append("Smartphone user (higher digital engagement)")
    if ctx.previously_clicked_whatsapp:
        factors.append("Previously clicked WhatsApp campaigns")
    if not factors:
        factors = ["Baseline engagement estimate"]

    components = {
        "calibrated_probability": None,
        "engagement_scaled": round(score, 4),
        "top_factors": factors,
        "model_used": False,
    }
    return score, components


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 3: DELIVERY INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════

def check_suppress(
    last_message_date: Optional[date],
    scoring_date: date,
    intervention_priority: float,
) -> Tuple[bool, Optional[str]]:
    """Fatigue suppression guard."""
    if last_message_date is None:
        return False, None

    days_since = (scoring_date - last_message_date).days

    if days_since <= HARD_SUPPRESS_DAYS:
        return True, (
            f"Hard fatigue guard: messaged {days_since}d ago "
            f"(threshold={HARD_SUPPRESS_DAYS}d)."
        )

    if days_since <= SOFT_SUPPRESS_DAYS and intervention_priority < SOFT_THRESHOLD:
        return True, (
            f"Soft fatigue guard: messaged {days_since}d ago and "
            f"intervention_priority {intervention_priority:.2f} < {SOFT_THRESHOLD} threshold."
        )

    return False, None


def recommend_channel(
    urgency: float,
    engagement: float,
    device_type: str,
    suppress: bool,
    whatsapp_enabled: bool = False,
) -> ChannelRecommendation:
    """
    Channel recommendation based on urgency × engagement matrix.

    High urgency + Low engagement → escalate (voice_call, field_visit)
    High urgency + High engagement → whatsapp (they'll respond)
    Low urgency + any → whatsapp or sms (low-cost)
    Suppressed → suppress
    """
    if suppress:
        return ChannelRecommendation.suppress

    if whatsapp_enabled:
        return ChannelRecommendation.whatsapp

    if urgency >= 0.7 and engagement < 0.3:
        # Critical situation but farmer unlikely to respond digitally
        if device_type == "keypad":
            return ChannelRecommendation.field_visit
        return ChannelRecommendation.voice_call

    if urgency >= 0.7 and engagement >= 0.3:
        return ChannelRecommendation.whatsapp

    if urgency >= 0.4:
        if device_type == "smartphone":
            return ChannelRecommendation.whatsapp
        return ChannelRecommendation.sms

    # Low urgency
    if device_type == "smartphone":
        return ChannelRecommendation.whatsapp
    return ChannelRecommendation.sms


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def _compute_engagement_confidence(engagement_components: dict) -> float:
    """
    Returns a confidence weight in [0.0, 1.0] for the engagement score.

    - Full ML model with known grower: 1.0 (full confidence)
    - Cold-start with population priors: 0.5 (partial confidence)
    - Heuristic fallback (no model): 0.3 (low confidence)

    When confidence is low, the priority formula shifts weight toward
    the agronomic urgency score, preventing noisy ML from distorting priorities.
    """
    if engagement_components.get("model_used", False):
        if engagement_components.get("cold_start", False):
            return 0.5  # priors available but no individual history
        return 1.0  # full ML prediction for known grower
    return 0.3  # pure heuristic, minimal confidence


def _compute_system_confidence(
    ctx: FarmerContext,
    engagement_components: dict,
    engagement_confidence: float,
) -> float:
    """
    Overall system confidence in the scoring decision.

    Factors:
      - Engagement model confidence (cold-start vs full ML)
      - Feature completeness (are optional fields provided?)
      - Agronomic input quality (non-zero, non-default values)
    """
    # Base from engagement confidence
    conf = engagement_confidence * 0.5

    # Feature completeness bonus
    completeness = 0.0
    if ctx.grower_farm_size is not None:
        completeness += 0.15
    if ctx.grower_age is not None:
        completeness += 0.10
    if ctx.device_type.value != "unknown":
        completeness += 0.10
    if ctx.last_message_date is not None:
        completeness += 0.15
    conf += completeness

    # Agronomic input quality (non-trivial inputs = higher confidence)
    inputs_provided = sum(1 for v in [ctx.pest_risk, ctx.weather_anomaly, ctx.crop_vulnerability] if v > 0.01)
    conf += inputs_provided * 0.05

    return _clip(conf, 0.0, 1.0)


def compute_urgency(ctx: FarmerContext) -> UrgencyResponse:
    """
    Main entry point — M7 Hybrid Intelligence Engine.

    1. Computes agronomic urgency (rule-based, deterministic)
    2. Predicts engagement likelihood (ML or heuristic)
    3. Fuses into priority score with channel recommendation
    4. Applies fatigue suppression guard
    """
    ctx = _UrgencyContext(ctx)
    # Layer 1: Agronomic urgency
    urgency_raw, urgency_components = score_urgency(ctx)
    urgency_score = round(urgency_raw, 2)

    # Layer 2: Behavioral engagement
    engagement_raw, engagement_components = score_engagement(ctx)
    engagement_score = round(engagement_raw, 2)

    # Layer 3: Fusion → priority score
    # Confidence-aware weighting: downweight ML when confidence is weak
    # Cold-start or heuristic = low confidence → lean on urgency
    engagement_confidence = _compute_engagement_confidence(engagement_components)
    effective_eng_weight = ENGAGEMENT_WEIGHT * engagement_confidence
    effective_urg_weight = 1.0 - effective_eng_weight

    priority_raw = (
        effective_urg_weight * urgency_raw +
        effective_eng_weight * engagement_raw
    )
    intervention_priority = round(_clip(priority_raw, 0.0, 1.0), 2)

    # Fatigue guard (applied to intervention priority)
    suppress, suppress_reason = check_suppress(
        ctx.last_message_date, ctx.scoring_date, intervention_priority
    )

    # Channel recommendation
    channel = recommend_channel(
        urgency_raw, engagement_raw, ctx.device_type.value, suppress, ctx.whatsapp_enabled
    )

    # Merge top factors from both layers
    all_factors = urgency_components["top_factors"] + engagement_components["top_factors"]
    # Deduplicate while preserving order
    seen = set()
    top_factors = []
    for f in all_factors:
        if f not in seen:
            seen.add(f)
            top_factors.append(f)
    top_factors = top_factors[:3]

    # ── Confidence score ───────────────────────────────────────────────
    # Confidence depends on: data availability, feature completeness, model state
    confidence = _compute_system_confidence(ctx, engagement_components, engagement_confidence)

    # ── Intervention economics ─────────────────────────────────────────
    # expected_value = (success_probability × benefit) − cost
    channel_cost = CHANNEL_COSTS.get(channel.value, 0.1)
    success_prob = engagement_raw * urgency_raw  # joint probability of need + response
    expected_value = round((success_prob * INTERVENTION_BENEFIT) - channel_cost, 4)

    return UrgencyResponse(
        grower_id=ctx.grower_id,
        urgency_score=urgency_score,
        urgency_components=urgency_components,
        engagement_score=engagement_score,
        engagement_components=engagement_components,
        intervention_priority=intervention_priority,
        recommended_channel=channel,
        suppress=suppress,
        suppress_reason=suppress_reason,
        top_factors=top_factors,
        confidence=round(confidence, 2),
        expected_intervention_value=expected_value,
        model_version=MODEL_VERSION,
    )


def _clip(val, minimum, maximum):
    return max(minimum, min(maximum, val))


# Keep backward-compatible alias
clip = _clip
