"""
M8 Product Ranker — Unit Tests
Syngenta IITM Hackathon 2026

Tests the 3 required scenarios + edge cases:
  - rice + fungal (no exact match → fallback)
  - cotton + aphid
  - wheat + rust

Run: pytest test/test_ranker.py -v
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from models import RankRequest, CropType, PestType, CropStage
from ranker import rank_products
from product_catalog import (
    PRODUCT_CATALOG, compute_efficacy_score,
    get_products_for_crop, get_products_for_pest, get_moa_group,
)


# ══════════════════════════════════════════════════════════════════════════════
# SCENARIO TESTS (from spec)
# ══════════════════════════════════════════════════════════════════════════════
class TestScenario_WheatRust:
    """wheat + rust → should recommend fungicides (Score, Amistar, Tilt, Alto)"""

    def setup_method(self):
        self.request = RankRequest(crop=CropType.wheat, pest=PestType.rust, urgency_score=0.8)
        self.result = rank_products(self.request)

    def test_returns_products(self):
        assert len(self.result.top_products) == 2

    def test_top_product_targets_rust(self):
        top = self.result.top_products[0]
        info = PRODUCT_CATALOG.get(top.product_name, {})
        assert "rust" in info.get("target_pests", set())

    def test_top_product_targets_wheat(self):
        top = self.result.top_products[0]
        info = PRODUCT_CATALOG.get(top.product_name, {})
        assert "wheat" in info.get("target_crops", set())

    def test_match_score_is_high(self):
        assert self.result.top_products[0].match_score > 0.3

    def test_has_match_reasons(self):
        assert len(self.result.top_products[0].match_reasons) > 0

    def test_not_fallback(self):
        assert self.result.fallback_used is False


class TestScenario_ChickpeaAphid:
    """chickpea + aphid → should recommend insecticide/seed treatment targeting aphids"""

    def setup_method(self):
        self.request = RankRequest(crop=CropType.chickpea, pest=PestType.aphid, urgency_score=0.6)
        self.result = rank_products(self.request)

    def test_top_product_targets_aphid(self):
        top = self.result.top_products[0]
        info = PRODUCT_CATALOG.get(top.product_name, {})
        assert "aphid" in info.get("target_pests", set())

    def test_top_product_targets_chickpea(self):
        top = self.result.top_products[0]
        info = PRODUCT_CATALOG.get(top.product_name, {})
        assert "chickpea" in info.get("target_crops", set())


class TestScenario_PotatoBlight:
    """potato + blight → should recommend Kavach 75 WP"""

    def setup_method(self):
        self.request = RankRequest(crop=CropType.potato, pest=PestType.blight, urgency_score=0.9)
        self.result = rank_products(self.request)

    def test_kavach_in_top(self):
        names = [p.product_name for p in self.result.top_products]
        assert "Kavach 75 WP" in names

    def test_urgency_boost_applied(self):
        # High urgency should favor curative/rescue products
        top = self.result.top_products[0]
        # Kavach is preventive, but at 0.9 urgency the efficacy score
        # still includes treatment intent alignment
        assert top.match_score > 0.5
        assert top.confidence > 0.5


class TestScenario_WheatWeeds:
    """wheat + weeds → should recommend Topik or Axial (herbicides)"""

    def setup_method(self):
        self.request = RankRequest(crop=CropType.wheat, pest=PestType.weeds, crop_stage=CropStage.tillering)
        self.result = rank_products(self.request)

    def test_herbicide_recommended(self):
        top = self.result.top_products[0]
        info = PRODUCT_CATALOG.get(top.product_name, {})
        assert info.get("category") == "herbicide"

    def test_stage_match(self):
        top = self.result.top_products[0]
        info = PRODUCT_CATALOG.get(top.product_name, {})
        assert "tillering" in info.get("effective_stages", set())


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCT CATALOG TESTS
# ══════════════════════════════════════════════════════════════════════════════
class TestProductCatalog:

    def test_catalog_has_12_products(self):
        assert len(PRODUCT_CATALOG) == 12

    def test_all_products_have_required_fields(self):
        for name, info in PRODUCT_CATALOG.items():
            assert "category" in info
            assert "target_pests" in info
            assert "target_crops" in info
            assert "effective_stages" in info

    def test_crop_filter_works(self):
        wheat_products = get_products_for_crop("wheat")
        assert len(wheat_products) > 0
        assert "Topik 15 WP" in wheat_products

    def test_pest_filter_works(self):
        rust_products = get_products_for_pest("rust")
        assert len(rust_products) > 0
        assert "Score 250 EC" in rust_products

    def test_rule_score_perfect_match(self):
        score = compute_efficacy_score("Actara 25 WG", "chickpea", "aphid", "flowering", 0.7)
        assert score > 0.85  # crop + pest + stage + efficacy all contribute

    def test_rule_score_no_match(self):
        score = compute_efficacy_score("Topik 15 WP", "potato", "aphid", "flowering", 0.5)
        assert score < 0.4  # herbicide doesn't match potato+aphid


# ══════════════════════════════════════════════════════════════════════════════
# EDGE CASES
# ══════════════════════════════════════════════════════════════════════════════
class TestEdgeCases:

    def test_general_pest_returns_results(self):
        req = RankRequest(crop=CropType.wheat, pest=PestType.general)
        result = rank_products(req)
        assert len(result.top_products) > 0

    def test_top_k_respected(self):
        req = RankRequest(crop=CropType.wheat, pest=PestType.rust, top_k=5)
        result = rank_products(req)
        assert len(result.top_products) == 5

    def test_response_has_all_fields(self):
        req = RankRequest(crop=CropType.mustard, pest=PestType.fungal)
        result = rank_products(req)
        assert result.crop == "mustard"
        assert result.pest == "fungal"
        assert result.model_version is not None
        assert len(result.top_products) > 0
        for p in result.top_products:
            assert p.product_name
            assert 0.0 <= p.match_score <= 2.0
            assert 0.0 <= p.confidence <= 1.0
            assert len(p.match_reasons) > 0
            assert "efficacy" in p.score_breakdown
            assert "adoption" in p.score_breakdown
            assert "moa_group" in p.score_breakdown

    def test_district_personalization(self):
        req1 = RankRequest(crop=CropType.wheat, pest=PestType.rust, district="Jaipur")
        req2 = RankRequest(crop=CropType.wheat, pest=PestType.rust, district="Ludhiana")
        r1 = rank_products(req1)
        r2 = rank_products(req2)
        # Scores may differ due to district-level signals
        # Just verify both return valid results
        assert len(r1.top_products) > 0
        assert len(r2.top_products) > 0



# ══════════════════════════════════════════════════════════════════════════════
# NEW FEATURE TESTS
# ══════════════════════════════════════════════════════════════════════════════
class TestMoADiversity:
    """Top-k recommendations should have different Modes of Action."""

    def test_top_3_have_diverse_moa(self):
        req = RankRequest(crop=CropType.wheat, pest=PestType.rust, top_k=3)
        result = rank_products(req)
        moa_groups = [get_moa_group(p.product_name) for p in result.top_products]
        # Filter out unknowns
        known_moa = [m for m in moa_groups if m != "unknown"]
        # Should have at least 2 different MoA groups in top 3
        assert len(set(known_moa)) >= 2


class TestConfidence:
    """Confidence should vary based on match quality."""

    def test_strong_match_high_confidence(self):
        req = RankRequest(crop=CropType.wheat, pest=PestType.rust, district="Jaipur")
        result = rank_products(req)
        assert result.top_products[0].confidence >= 0.5

    def test_weak_match_lower_confidence(self):
        req = RankRequest(crop=CropType.safflower, pest=PestType.general)
        result = rank_products(req)
        # Safflower has fewer product matches → lower confidence
        assert result.top_products[0].confidence <= 0.9


class TestTreatmentIntent:
    """High urgency should prefer curative; low urgency should prefer preventive."""

    def test_high_urgency_prefers_curative(self):
        req = RankRequest(crop=CropType.wheat, pest=PestType.rust, urgency_score=0.95)
        result = rank_products(req)
        top = result.top_products[0]
        intents = top.score_breakdown.get("treatment_intent", [])
        # Should prefer curative or rescue
        assert "curative" in intents or "rescue" in intents

    def test_seed_treatment_penalized_at_flowering(self):
        req = RankRequest(crop=CropType.wheat, pest=PestType.wilt, crop_stage=CropStage.flowering)
        result = rank_products(req)
        # Seed treatments should NOT be top recommendation at flowering
        for p in result.top_products:
            info = PRODUCT_CATALOG.get(p.product_name, {})
            if info.get("application_mode") == "seed":
                assert p.match_score < 0.3  # heavily penalized


class TestAffordability:
    """Small farmers should get cost-effective recommendations."""

    def test_small_farmer_prefers_affordable(self):
        req = RankRequest(crop=CropType.wheat, pest=PestType.rust, grower_farm_size=1.5)
        result = rank_products(req)
        top = result.top_products[0]
        # Should not be premium-only for small farmer
        tier = top.score_breakdown.get("price_tier", "mid")
        assert tier in ("low", "mid")  # affordable options preferred


class TestSprayHistoryResistance:
    """Spray history should trigger resistance penalties and advisories."""

    def test_recently_used_product_penalized(self):
        req = RankRequest(
            crop=CropType.wheat, pest=PestType.rust,
            recently_used_products=["Score 250 EC"],
            top_k=3,
        )
        result = rank_products(req)
        # Score 250 EC should be penalized (same product recently)
        scores = {p.product_name: p.match_score for p in result.top_products}
        # It should either not be in top or have lower score
        if "Score 250 EC" in scores:
            # If it still appears, it should be ranked lower than alternatives
            other_scores = [s for n, s in scores.items() if n != "Score 250 EC"]
            assert any(s > scores["Score 250 EC"] for s in other_scores)

    def test_same_moa_penalized(self):
        # Tilt and Score are both FRAC-3 (triazoles)
        req = RankRequest(
            crop=CropType.wheat, pest=PestType.rust,
            recently_used_products=["Tilt 250 EC"],
            top_k=3,
        )
        result = rank_products(req)
        # Score 250 EC (also FRAC-3) should be penalized
        names = [p.product_name for p in result.top_products]
        # Amistar (FRAC-11) should rank higher than Score (FRAC-3)
        if "Amistar 250 SC" in names and "Score 250 EC" in names:
            amistar_idx = names.index("Amistar 250 SC")
            score_idx = names.index("Score 250 EC")
            assert amistar_idx < score_idx

    def test_resistance_advisory_generated(self):
        req = RankRequest(
            crop=CropType.wheat, pest=PestType.rust,
            spray_history=["Score 250 EC", "Tilt 250 EC", "Alto 5 SC"],  # all FRAC-3
        )
        result = rank_products(req)
        assert result.resistance_advisory is not None
        assert "FRAC-3" in result.resistance_advisory

    def test_no_advisory_without_history(self):
        req = RankRequest(crop=CropType.wheat, pest=PestType.rust)
        result = rank_products(req)
        assert result.resistance_advisory is None


class TestWhyNotRecommended:
    """Should explain why certain products were rejected."""

    def test_rejections_present(self):
        req = RankRequest(crop=CropType.wheat, pest=PestType.rust, grower_farm_size=1.0, top_k=2)
        result = rank_products(req)
        assert result.not_recommended is not None
        assert len(result.not_recommended) > 0

    def test_rejection_has_reasons(self):
        req = RankRequest(crop=CropType.wheat, pest=PestType.rust, top_k=2)
        result = rank_products(req)
        if result.not_recommended:
            for rej in result.not_recommended:
                assert len(rej.not_ranked_higher_because) > 0


class TestDynamicWeighting:
    """Urgency should shift weights toward efficacy."""

    def test_high_urgency_weights_favor_efficacy(self):
        req_high = RankRequest(crop=CropType.wheat, pest=PestType.rust, urgency_score=0.95)
        result = rank_products(req_high)
        weights = result.top_products[0].score_breakdown.get("weights_used", {})
        assert weights["efficacy"] > 0.55  # should be ~0.59

    def test_low_urgency_weights_favor_adoption(self):
        req_low = RankRequest(crop=CropType.wheat, pest=PestType.rust, urgency_score=0.1)
        result = rank_products(req_low)
        weights = result.top_products[0].score_breakdown.get("weights_used", {})
        assert weights["adoption"] > 0.25  # should be ~0.285


class TestContraindications:
    """Products should be penalized near harvest or wrong stage."""

    def test_near_harvest_penalizes_foliar(self):
        req = RankRequest(
            crop=CropType.wheat, pest=PestType.rust,
            days_to_harvest=5, top_k=3,
        )
        result = rank_products(req)
        # All foliar products should have reduced scores
        for p in result.top_products:
            info = PRODUCT_CATALOG.get(p.product_name, {})
            if info.get("application_mode") == "foliar":
                assert p.match_score < 0.5  # heavily penalized
