"""
M7 Intelligence Engine — Unit Tests
Syngenta IITM Hackathon 2026

Tests the 3-layer hybrid architecture:
  Layer 1: Agronomic urgency (formula)
  Layer 2: Behavioral engagement (ML / cold-start / heuristic)
  Layer 3: Delivery intelligence (priority + channel + suppression)

Run: pytest test/test_scorer.py -v
"""

import sys
import os
from datetime import date, timedelta
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from shared.models import CropType, DeviceType, ChannelRecommendation

class FarmerContext:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
from urgency_scorer.app.scorer import (
    compute_urgency, score_urgency, score_engagement,
    compute_recency_penalty, check_suppress, recommend_channel,
)


# ── Helpers ────────────────────────────────────────────────────────────────────
def make_ctx(**kwargs) -> FarmerContext:
    defaults = dict(
        grower_id="G_TEST",
        crop=CropType.wheat,
        pest_risk=0.5,
        weather_anomaly=0.5,
        crop_vulnerability=0.5,
        last_message_date=None,
        scoring_date=date(2026, 1, 15),
    )
    defaults.update(kwargs)
    return FarmerContext(**defaults)


def score_without_ml(ctx: FarmerContext):
    """Force heuristic engagement by mocking out the model loader."""
    with patch("urgency_scorer.app.scorer._load_model", return_value=None):
        return compute_urgency(ctx)


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 1: AGRONOMIC URGENCY TESTS
# Formula: 0.40×pest + 0.30×weather + 0.20×vuln + 0.10×(1 − recency)
# ══════════════════════════════════════════════════════════════════════════════
class TestLayer1_AgronomicUrgency:

    def test_high_urgency_all_risks(self):
        ctx = make_ctx(pest_risk=1.0, weather_anomaly=0.9, crop_vulnerability=0.95)
        score, _ = score_urgency(ctx)
        # 0.40 + 0.27 + 0.19 + 0.10 = 0.96
        assert 0.90 <= score <= 1.00

    def test_zero_risk_still_has_recency_bonus(self):
        ctx = make_ctx(pest_risk=0.0, weather_anomaly=0.0, crop_vulnerability=0.0)
        score, comps = score_urgency(ctx)
        # With zero risk inputs, only the communication_window term contributes
        # Score should equal the recency_term (whatever weight is used)
        assert score > 0.0  # not zero — recency bonus exists
        assert abs(score - comps["recency_term"]) < 0.001

    def test_formula_is_deterministic(self):
        ctx = make_ctx(pest_risk=0.7, weather_anomaly=0.5, crop_vulnerability=0.3)
        s1, _ = score_urgency(ctx)
        s2, _ = score_urgency(ctx)
        assert s1 == s2

    def test_pest_risk_dominates(self):
        ctx_pest = make_ctx(pest_risk=1.0, weather_anomaly=0.0, crop_vulnerability=0.0)
        ctx_weather = make_ctx(pest_risk=0.0, weather_anomaly=1.0, crop_vulnerability=0.0)
        s_pest, _ = score_urgency(ctx_pest)
        s_weather, _ = score_urgency(ctx_weather)
        assert s_pest > s_weather  # 0.40 > 0.30

    def test_recency_penalty_reduces_score(self):
        scoring_date = date(2026, 1, 15)
        ctx_recent = make_ctx(last_message_date=scoring_date - timedelta(days=1), scoring_date=scoring_date)
        ctx_old = make_ctx(last_message_date=scoring_date - timedelta(days=30), scoring_date=scoring_date)
        s_recent, _ = score_urgency(ctx_recent)
        s_old, _ = score_urgency(ctx_old)
        assert s_old > s_recent  # old message = higher recency bonus

    def test_components_returned(self):
        ctx = make_ctx(pest_risk=0.8, weather_anomaly=0.6, crop_vulnerability=0.4)
        _, comps = score_urgency(ctx)
        assert "pest_risk_term" in comps
        assert "weather_anomaly_term" in comps
        assert "crop_vulnerability_term" in comps
        assert "recency_term" in comps
        assert "top_factors" in comps
        assert len(comps["top_factors"]) > 0

    def test_score_always_in_0_1(self):
        for pr, wa, cv in [(0, 0, 0), (1, 1, 1), (0.5, 0.5, 0.5)]:
            ctx = make_ctx(pest_risk=pr, weather_anomaly=wa, crop_vulnerability=cv)
            score, _ = score_urgency(ctx)
            assert 0.0 <= score <= 1.0


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2: BEHAVIORAL ENGAGEMENT TESTS
# ══════════════════════════════════════════════════════════════════════════════
class TestLayer2_Engagement:

    def test_heuristic_fallback_returns_score(self):
        """When no model exists, heuristic should still return a valid score."""
        ctx = make_ctx(device_type=DeviceType.smartphone)
        with patch("urgency_scorer.app.scorer._load_model", return_value=None):
            score, comps = score_engagement(ctx)
        assert 0.0 <= score <= 1.0
        assert comps["model_used"] is False

    def test_smartphone_boosts_engagement(self):
        ctx_smart = make_ctx(device_type=DeviceType.smartphone)
        ctx_keypad = make_ctx(device_type=DeviceType.keypad)
        with patch("urgency_scorer.app.scorer._load_model", return_value=None):
            s_smart, _ = score_engagement(ctx_smart)
            s_keypad, _ = score_engagement(ctx_keypad)
        assert s_smart > s_keypad

    def test_previously_clicked_boosts_engagement(self):
        ctx_clicked = make_ctx(previously_clicked_whatsapp=True, device_type=DeviceType.smartphone)
        ctx_no_click = make_ctx(previously_clicked_whatsapp=False, device_type=DeviceType.smartphone)
        with patch("urgency_scorer.app.scorer._load_model", return_value=None):
            s_clicked, _ = score_engagement(ctx_clicked)
            s_no_click, _ = score_engagement(ctx_no_click)
        assert s_clicked > s_no_click

    def test_cold_start_for_unknown_grower(self):
        """New farmer not in training data should use population priors."""
        # Create a mock payload with population priors
        mock_payload = {
            "pipeline": None,  # won't be used for cold-start
            "grower_geo_map": {},  # empty = grower not known
            "grower_profile_map": {},  # empty = grower not known
            "district_ctr_map": {"nashik": 0.08},
            "global_ctr": 0.05,
            "population_priors": {
                "global_ctr": 0.05,
                "district_ctr_map": {"nashik": 0.08},
                "crop_ctr_map": {"wheat": 0.06, "potato": 0.04},
                "device_ctr": {"smartphone": 0.07, "keypad": 0.03, "unknown": 0.05},
                "median_farm_size": 3.0,
                "median_age": 40.0,
            },
            "min_prob": 0.02,
            "max_prob": 0.15,
            "feature_importances": {},
        }
        ctx = make_ctx(grower_id="NEW_FARMER_999")
        with patch("urgency_scorer.app.scorer._load_model", return_value=mock_payload):
            score, comps = score_engagement(ctx)
        assert 0.0 <= score <= 1.0
        assert comps["cold_start"] is True
        assert "priors_used" in comps


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 3: DELIVERY INTELLIGENCE TESTS
# ══════════════════════════════════════════════════════════════════════════════
class TestLayer3_DeliveryIntelligence:

    def test_priority_is_weighted_combination(self):
        ctx = make_ctx(pest_risk=0.8, weather_anomaly=0.6, crop_vulnerability=0.5)
        result = score_without_ml(ctx)
        # With heuristic fallback, confidence = 0.3
        # effective_eng_weight = 0.30 * 0.3 = 0.09
        # effective_urg_weight = 1.0 - 0.09 = 0.91
        # priority ≈ 0.91 * urgency + 0.09 * engagement
        # Just verify it's between urgency and engagement, weighted toward urgency
        assert result.intervention_priority >= min(result.urgency_score, result.engagement_score)
        assert result.intervention_priority <= max(result.urgency_score, result.engagement_score)
        # And closer to urgency (since confidence is low)
        dist_to_urgency = abs(result.intervention_priority - result.urgency_score)
        dist_to_engagement = abs(result.intervention_priority - result.engagement_score)
        assert dist_to_urgency <= dist_to_engagement

    def test_high_urgency_low_engagement_escalates_channel(self):
        channel = recommend_channel(urgency=0.85, engagement=0.15, device_type="keypad", suppress=False)
        assert channel == ChannelRecommendation.field_visit

    def test_high_urgency_low_engagement_smartphone_gets_voice(self):
        channel = recommend_channel(urgency=0.85, engagement=0.15, device_type="smartphone", suppress=False)
        assert channel == ChannelRecommendation.voice_call

    def test_high_urgency_high_engagement_gets_whatsapp(self):
        channel = recommend_channel(urgency=0.80, engagement=0.5, device_type="smartphone", suppress=False)
        assert channel == ChannelRecommendation.whatsapp

    def test_suppressed_gets_suppress_channel(self):
        channel = recommend_channel(urgency=0.9, engagement=0.9, device_type="smartphone", suppress=True)
        assert channel == ChannelRecommendation.suppress


# ══════════════════════════════════════════════════════════════════════════════
# FATIGUE SUPPRESSION TESTS
# ══════════════════════════════════════════════════════════════════════════════
class TestFatigueSuppression:

    def test_no_message_no_suppress(self):
        suppress, reason = check_suppress(None, date(2026, 1, 15), 0.3)
        assert suppress is False

    def test_hard_suppress_within_3_days(self):
        scoring_date = date(2026, 1, 15)
        suppress, reason = check_suppress(scoring_date - timedelta(days=2), scoring_date, 0.9)
        assert suppress is True
        assert "Hard" in reason

    def test_hard_suppress_at_boundary(self):
        scoring_date = date(2026, 1, 15)
        suppress, _ = check_suppress(scoring_date - timedelta(days=3), scoring_date, 0.9)
        assert suppress is True

    def test_outside_hard_window_high_priority_passes(self):
        scoring_date = date(2026, 1, 15)
        suppress, _ = check_suppress(scoring_date - timedelta(days=4), scoring_date, 0.7)
        assert suppress is False

    def test_soft_suppress_low_priority(self):
        scoring_date = date(2026, 1, 15)
        suppress, reason = check_suppress(scoring_date - timedelta(days=5), scoring_date, 0.3)
        assert suppress is True
        assert "Soft" in reason

    def test_soft_bypass_high_priority(self):
        scoring_date = date(2026, 1, 15)
        suppress, _ = check_suppress(scoring_date - timedelta(days=5), scoring_date, 0.6)
        assert suppress is False

    def test_outside_soft_window_always_passes(self):
        scoring_date = date(2026, 1, 15)
        suppress, _ = check_suppress(scoring_date - timedelta(days=8), scoring_date, 0.1)
        assert suppress is False


# ══════════════════════════════════════════════════════════════════════════════
# RECENCY PENALTY TESTS
# ══════════════════════════════════════════════════════════════════════════════
class TestRecencyPenalty:

    def test_never_messaged_is_zero(self):
        assert compute_recency_penalty(None, date.today()) == 0.0

    def test_decreases_over_time(self):
        today = date(2026, 1, 15)
        p1 = compute_recency_penalty(today - timedelta(days=1), today)
        p7 = compute_recency_penalty(today - timedelta(days=7), today)
        p30 = compute_recency_penalty(today - timedelta(days=30), today)
        assert p1 > p7 > p30

    def test_half_life_at_soft_window(self):
        today = date(2026, 1, 15)
        penalty = compute_recency_penalty(today - timedelta(days=7), today, soft_window=7)
        assert abs(penalty - 0.5) < 0.02

    def test_same_day_is_max(self):
        today = date(2026, 1, 15)
        penalty = compute_recency_penalty(today, today)
        assert penalty == 1.0


# ══════════════════════════════════════════════════════════════════════════════
# END-TO-END INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════════════
class TestEndToEnd:

    def test_new_farmer_cold_start_works(self):
        """Brand new farmer with no history — system should not crash."""
        ctx = make_ctx(
            grower_id="BRAND_NEW_FARMER",
            pest_risk=0.82,
            weather_anomaly=0.71,
            crop_vulnerability=0.66,
            last_message_date=None,
        )
        result = score_without_ml(ctx)
        assert 0.0 <= result.urgency_score <= 1.0
        assert 0.0 <= result.engagement_score <= 1.0
        assert 0.0 <= result.intervention_priority <= 1.0
        assert result.suppress is False
        assert result.recommended_channel != ChannelRecommendation.suppress

    def test_high_urgency_never_messaged(self):
        ctx = make_ctx(pest_risk=0.95, weather_anomaly=0.85, crop_vulnerability=0.9)
        result = score_without_ml(ctx)
        assert result.urgency_score >= 0.85
        assert result.suppress is False

    def test_low_urgency_recently_messaged_suppressed(self):
        scoring_date = date(2026, 1, 15)
        ctx = make_ctx(
            pest_risk=0.1, weather_anomaly=0.1, crop_vulnerability=0.1,
            last_message_date=scoring_date - timedelta(days=1),
            scoring_date=scoring_date,
        )
        result = score_without_ml(ctx)
        assert result.suppress is True

    def test_response_has_all_fields(self):
        ctx = make_ctx()
        result = score_without_ml(ctx)
        assert hasattr(result, "urgency_score")
        assert hasattr(result, "urgency_components")
        assert hasattr(result, "engagement_score")
        assert hasattr(result, "engagement_components")
        assert hasattr(result, "intervention_priority")
        assert hasattr(result, "recommended_channel")
        assert hasattr(result, "suppress")
        assert hasattr(result, "top_factors")
        assert hasattr(result, "model_version")
        assert hasattr(result, "confidence")
        assert hasattr(result, "expected_intervention_value")
        assert 0.0 <= result.confidence <= 1.0

    def test_model_version_is_hybrid(self):
        ctx = make_ctx()
        result = score_without_ml(ctx)
        assert "hybrid" in result.model_version

    def test_urgency_score_matches_formula(self):
        """Verify the urgency score uses the weighted formula structure."""
        ctx = make_ctx(
            pest_risk=0.6, weather_anomaly=0.4, crop_vulnerability=0.3,
            last_message_date=None,
        )
        result = score_without_ml(ctx)
        # Verify components sum to the score (regardless of which weights are used)
        comps = result.urgency_components
        component_sum = (
            comps["pest_risk_term"] +
            comps["weather_anomaly_term"] +
            comps["crop_vulnerability_term"] +
            comps["recency_term"]
        )
        assert abs(result.urgency_score - round(component_sum, 2)) <= 0.01
