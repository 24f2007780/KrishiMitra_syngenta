"""
M9 Campaign Receptivity — Prediction Engine
Syngenta IITM Hackathon 2026

═══════════════════════════════════════════════════════════════════
ARCHITECTURE: Segment Classification + Receptivity Prediction
           + Format Optimization + Timing Intelligence
═══════════════════════════════════════════════════════════════════

Layer 1 — Farmer Segmentation
    Classify farmer into behavioral segment based on engagement history.
    Segments: digital_active, digital_passive, offline_only, new_farmer

Layer 2 — Receptivity Prediction (ML)
    XGBoost trained on clicked_status with contextual features.
    Predicts: P(engagement | farmer_context, campaign_context)

Layer 3 — Format Optimization
    Given segment + context, recommend best creative format.
    Based on segment-level engagement patterns from historical data.

Layer 4 — Timing & Fatigue Intelligence
    When to send, and when to back off.

═══════════════════════════════════════════════════════════════════
"""

import os
import math
import pickle
import logging
from typing import Optional, Tuple, List
from datetime import date

import numpy as np

from shared.models import (
    ReceptivityRequest, ReceptivityResponse, FormatRecommendation,
    FarmerSegment, CampaignFormat,
)

logger = logging.getLogger(__name__)

MODEL_PATH = os.getenv("RECEPTIVITY_MODEL_PATH", "ml/receptivity_model.pkl")
MODEL_VERSION = "campaign-receptivity-v1"

_model_cache = None


def _load_model():
    global _model_cache
    if _model_cache is not None:
        return _model_cache
    try:
        with open(MODEL_PATH, "rb") as f:
            _model_cache = pickle.load(f)
        logger.info("Loaded receptivity model from %s", MODEL_PATH)
        return _model_cache
    except FileNotFoundError:
        logger.info("Receptivity model not found — using heuristic mode.")
        return None
    except Exception as exc:
        logger.error("Failed to load receptivity model: %s", exc)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1: FARMER SEGMENTATION
# ══════════════════════════════════════════════════════════════════════════════

def _classify_segment(request: ReceptivityRequest, payload: dict) -> Tuple[FarmerSegment, float]:
    """
    Classify farmer into behavioral segment.
    Uses engagement history if available, otherwise infers from profile.
    """
    # If we have historical engagement data
    if request.historical_click_rate is not None:
        if request.historical_click_rate > 0.08:
            return FarmerSegment.digital_active, 0.90
        elif request.historical_open_rate and request.historical_open_rate > 0.3:
            return FarmerSegment.digital_passive, 0.85
        else:
            return FarmerSegment.offline_only, 0.80

    # Check if grower exists in model's history
    if payload and request.grower_id:
        grower_segments = payload.get("grower_segments", {})
        if request.grower_id in grower_segments:
            seg_data = grower_segments[request.grower_id]
            return FarmerSegment(seg_data["segment"]), seg_data["confidence"]

    # Infer from profile signals
    if request.previously_clicked:
        return FarmerSegment.digital_active, 0.70

    if request.product_scanned:
        return FarmerSegment.digital_active, 0.65

    if request.device_type == "keypad":
        return FarmerSegment.offline_only, 0.75

    if request.device_type == "smartphone":
        if request.offline_campaign_attended:
            return FarmerSegment.digital_passive, 0.55
        return FarmerSegment.new_farmer, 0.50

    return FarmerSegment.new_farmer, 0.40


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2: RECEPTIVITY PREDICTION
# ══════════════════════════════════════════════════════════════════════════════

def _predict_receptivity(
    request: ReceptivityRequest,
    segment: FarmerSegment,
    payload: dict,
) -> Tuple[float, float]:
    """
    Predict overall campaign receptivity score.
    Returns (receptivity_score, confidence).
    """
    if payload and payload.get("pipeline"):
        # ML prediction
        fv = _build_features(request, segment, payload)
        pipeline = payload["pipeline"]
        prob = float(pipeline.predict_proba(fv)[0][1])

        # Scale to [0, 1] for interpretability
        min_p = payload.get("min_prob", 0.01)
        max_p = payload.get("max_prob", 0.15)
        receptivity = (prob - min_p) / (max_p - min_p)
        receptivity = max(0.0, min(1.0, receptivity))

        confidence = 0.80 if request.grower_id in payload.get("grower_segments", {}) else 0.55
        return receptivity, confidence

    # Heuristic fallback
    return _heuristic_receptivity(request, segment)


def _build_features(request: ReceptivityRequest, segment: FarmerSegment, payload: dict) -> np.ndarray:
    """Build feature vector for ML prediction."""
    # Segment encoding
    seg_map = {"digital_active": 3, "digital_passive": 2, "offline_only": 1, "new_farmer": 0}
    seg_val = seg_map.get(segment.value, 0)

    # Device encoding
    dev_map = {"smartphone": 2, "keypad": 1, "unknown": 0}
    dev_val = dev_map.get(request.device_type.value, 0)

    # Temporal features
    month = float(request.scoring_date.month)
    day_of_week = float(request.scoring_date.weekday())

    # Engagement history
    hist_open = request.historical_open_rate if request.historical_open_rate is not None else 0.23
    hist_click = request.historical_click_rate if request.historical_click_rate is not None else 0.05
    msgs_30d = float(request.messages_received_last_30d) if request.messages_received_last_30d is not None else 2.0

    # Profile
    farm_size = request.farm_size_acres if request.farm_size_acres is not None else 2.5
    age = float(request.grower_age) if request.grower_age is not None else 42.0
    scanned = 1.0 if request.product_scanned else 0.0
    attended = 1.0 if request.offline_campaign_attended else 0.0

    # District CTR
    district_ctr = payload.get("district_ctr_map", {}).get(request.district, payload.get("global_ctr", 0.05))

    # Crop engagement rate
    crop_ctr = payload.get("crop_ctr_map", {}).get(request.crop.value, 0.05)

    features = [
        seg_val, dev_val, month, day_of_week,
        hist_open, hist_click, msgs_30d,
        farm_size, age, scanned, attended,
        district_ctr, crop_ctr,
    ]
    return np.array(features, dtype=np.float32).reshape(1, -1)


def _heuristic_receptivity(request: ReceptivityRequest, segment: FarmerSegment) -> Tuple[float, float]:
    """Heuristic receptivity when no ML model available."""
    base_rates = {
        FarmerSegment.digital_active: 0.72,
        FarmerSegment.digital_passive: 0.40,
        FarmerSegment.offline_only: 0.15,
        FarmerSegment.new_farmer: 0.35,
    }
    score = base_rates.get(segment, 0.35)

    # Adjustments
    if request.product_scanned:
        score += 0.10
    if request.device_type.value == "smartphone":
        score += 0.05
    if request.messages_received_last_30d and request.messages_received_last_30d > 4:
        score -= 0.15  # fatigue

    score = max(0.0, min(1.0, score))
    return score, 0.45  # low confidence for heuristic


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 3: FORMAT OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════════════

# Segment → format engagement rates (learned from data patterns)
SEGMENT_FORMAT_RATES = {
    FarmerSegment.digital_active: {
        CampaignFormat.whatsapp_image: 0.18,
        CampaignFormat.whatsapp_video: 0.15,
        CampaignFormat.whatsapp_text: 0.08,
        CampaignFormat.sms_short: 0.04,
        CampaignFormat.voice_ivr: 0.06,
        CampaignFormat.field_demo: 0.12,
    },
    FarmerSegment.digital_passive: {
        CampaignFormat.whatsapp_image: 0.09,
        CampaignFormat.whatsapp_video: 0.07,
        CampaignFormat.whatsapp_text: 0.04,
        CampaignFormat.sms_short: 0.05,
        CampaignFormat.voice_ivr: 0.08,
        CampaignFormat.field_demo: 0.14,
    },
    FarmerSegment.offline_only: {
        CampaignFormat.whatsapp_image: 0.02,
        CampaignFormat.whatsapp_video: 0.01,
        CampaignFormat.whatsapp_text: 0.01,
        CampaignFormat.sms_short: 0.06,
        CampaignFormat.voice_ivr: 0.12,
        CampaignFormat.field_demo: 0.22,
    },
    FarmerSegment.new_farmer: {
        CampaignFormat.whatsapp_image: 0.07,
        CampaignFormat.whatsapp_video: 0.06,
        CampaignFormat.whatsapp_text: 0.04,
        CampaignFormat.sms_short: 0.05,
        CampaignFormat.voice_ivr: 0.08,
        CampaignFormat.field_demo: 0.10,
    },
}

FORMAT_REASONING = {
    CampaignFormat.whatsapp_image: "Visual crop protection imagery drives highest digital engagement",
    CampaignFormat.whatsapp_video: "Short demo videos show application technique effectively",
    CampaignFormat.whatsapp_text: "Low-cost text format for routine advisory messages",
    CampaignFormat.sms_short: "Reaches keypad users; concise actionable message",
    CampaignFormat.voice_ivr: "Voice in local language overcomes literacy barriers",
    CampaignFormat.field_demo: "In-person demonstration builds trust for new products",
}


def _recommend_formats(
    segment: FarmerSegment,
    request: ReceptivityRequest,
    receptivity: float,
) -> List[FormatRecommendation]:
    """Recommend best creative formats for this segment."""
    rates = SEGMENT_FORMAT_RATES.get(segment, SEGMENT_FORMAT_RATES[FarmerSegment.new_farmer])

    # Adjust for device
    adjusted = dict(rates)
    if request.device_type.value == "keypad":
        # Keypad users can't receive WhatsApp
        adjusted[CampaignFormat.whatsapp_image] = 0.0
        adjusted[CampaignFormat.whatsapp_video] = 0.0
        adjusted[CampaignFormat.whatsapp_text] = 0.0
        adjusted[CampaignFormat.sms_short] *= 1.5
        adjusted[CampaignFormat.voice_ivr] *= 1.5

    # Sort by predicted engagement
    sorted_formats = sorted(adjusted.items(), key=lambda x: x[1], reverse=True)

    recommendations = []
    for fmt, rate in sorted_formats[:3]:
        if rate < 0.01:
            continue
        # Confidence based on segment confidence and data availability
        conf = 0.7 if segment != FarmerSegment.new_farmer else 0.4
        recommendations.append(FormatRecommendation(
            format=fmt,
            predicted_engagement=round(rate, 3),
            confidence=conf,
            reasoning=FORMAT_REASONING.get(fmt, ""),
        ))

    return recommendations


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 4: TIMING & FATIGUE INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════

def _compute_fatigue_risk(request: ReceptivityRequest, segment: FarmerSegment) -> float:
    """Estimate message fatigue risk."""
    if request.messages_received_last_30d is None:
        return 0.3  # unknown → moderate default

    msgs = request.messages_received_last_30d

    # Segment-specific fatigue thresholds
    thresholds = {
        FarmerSegment.digital_active: 6,
        FarmerSegment.digital_passive: 3,
        FarmerSegment.offline_only: 1,
        FarmerSegment.new_farmer: 2,
    }
    threshold = thresholds.get(segment, 3)

    if msgs >= threshold * 2:
        return 0.95  # severe fatigue
    elif msgs >= threshold:
        return 0.65  # moderate fatigue
    elif msgs >= threshold * 0.5:
        return 0.30  # low fatigue
    return 0.10  # fresh


def _get_timing(segment: FarmerSegment, crop: str) -> Tuple[Optional[str], Optional[str]]:
    """Best day/time based on segment behavior patterns."""
    # Derived from agricultural communication patterns
    timing = {
        FarmerSegment.digital_active: ("Tuesday–Thursday", "9:00–11:00 AM"),
        FarmerSegment.digital_passive: ("Monday–Wednesday", "7:00–9:00 AM"),
        FarmerSegment.offline_only: ("Saturday", "10:00 AM–12:00 PM"),
        FarmerSegment.new_farmer: ("Wednesday–Friday", "8:00–10:00 AM"),
    }
    day, time = timing.get(segment, ("Wednesday", "9:00 AM"))
    return day, time


# ══════════════════════════════════════════════════════════════════════════════
# CREATIVE STRATEGY SUGGESTIONS
# ══════════════════════════════════════════════════════════════════════════════

def _generate_creative_suggestions(
    segment: FarmerSegment,
    request: ReceptivityRequest,
    fatigue_risk: float,
    receptivity: float,
) -> List[str]:
    """Generate actionable creative strategy suggestions."""
    suggestions = []

    # Segment-specific strategies
    if segment == FarmerSegment.digital_active:
        suggestions.append("Use product comparison visuals — this segment responds to data-driven content")
        if request.product_scanned:
            suggestions.append("Reference their scanned product — personalized follow-up drives 2× engagement")
    elif segment == FarmerSegment.digital_passive:
        suggestions.append("Lead with urgency/risk framing — passive users need stronger hooks")
        suggestions.append("Include clear single CTA — reduce decision friction")
    elif segment == FarmerSegment.offline_only:
        suggestions.append("Prioritize voice/IVR in local language over digital formats")
        suggestions.append("Coordinate with field rep visit for in-person demonstration")
    elif segment == FarmerSegment.new_farmer:
        suggestions.append("Start with educational content before product promotion")
        suggestions.append("Use social proof — 'farmers in your district are using...'")

    # Fatigue-aware suggestions
    if fatigue_risk > 0.6:
        suggestions.append("⚠️ High fatigue risk — reduce frequency or switch to high-value content only")
    elif fatigue_risk < 0.2:
        suggestions.append("Low fatigue — safe to increase message frequency this week")

    # Crop-specific timing
    crop = request.crop.value
    month = request.scoring_date.month
    if crop == "wheat" and month in (1, 2):
        suggestions.append("Wheat at critical stage — frame message around immediate crop protection need")
    elif crop == "potato" and month in (12, 1):
        suggestions.append("Potato blight season — lead with disease prevention urgency")

    # Receptivity-based
    if receptivity < 0.3:
        suggestions.append("Low receptivity predicted — consider escalating to field visit or voice call")

    return suggestions[:4]


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def predict_receptivity(request: ReceptivityRequest) -> ReceptivityResponse:
    """
    Main entry point — Campaign Receptivity Prediction Engine.

    1. Classifies farmer into behavioral segment
    2. Predicts overall receptivity (ML or heuristic)
    3. Recommends best creative formats
    4. Provides timing and fatigue intelligence
    5. Generates creative strategy suggestions
    """
    payload = _load_model()

    # Layer 1: Segmentation
    segment, seg_confidence = _classify_segment(request, payload or {})

    # Layer 2: Receptivity prediction
    receptivity, pred_confidence = _predict_receptivity(request, segment, payload)

    # Layer 3: Format optimization
    format_recs = _recommend_formats(segment, request, receptivity)

    # Layer 4: Timing & fatigue
    fatigue_risk = _compute_fatigue_risk(request, segment)
    best_day, best_time = _get_timing(segment, request.crop.value)

    # Creative suggestions
    suggestions = _generate_creative_suggestions(segment, request, fatigue_risk, receptivity)

    return ReceptivityResponse(
        grower_id=request.grower_id,
        segment=segment,
        segment_confidence=round(seg_confidence, 2),
        receptivity_score=round(receptivity, 2),
        recommended_formats=format_recs,
        best_day_of_week=best_day,
        best_time_window=best_time,
        fatigue_risk=round(fatigue_risk, 2),
        creative_suggestions=suggestions,
        model_version=MODEL_VERSION,
    )
