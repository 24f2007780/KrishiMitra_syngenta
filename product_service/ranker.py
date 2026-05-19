"""
M8 Product Ranker — Adaptive Agronomic Decision Engine
Syngenta IITM Hackathon 2026

═══════════════════════════════════════════════════════════════════
ARCHITECTURE: Efficacy + Adoption + Availability
           + Resistance Memory + Dynamic Urgency Weighting
═══════════════════════════════════════════════════════════════════

Layer 1 — Agronomic Efficacy (dynamic weight: 40–60%)
    How well does this product treat the problem?
    Weight increases with urgency.

Layer 2 — Behavioral Adoption (dynamic weight: 15–30%)
    Regional purchase affinity from POS patterns.
    Weight decreases with urgency.

Layer 3 — Availability & Affordability (dynamic weight: 15–25%)
    Stock levels + price tier matching.

Post-Processing:
    - Resistance management (MoA history tracking)
    - Recommendation diversity (different FRAC/IRAC groups)
    - "Why not recommended" explanations
    - Contraindication checks (pre-harvest interval, stage)
    - Confidence estimation

═══════════════════════════════════════════════════════════════════
"""

import os
import pickle
import logging
from typing import List, Tuple, Optional, Set, Dict
from collections import Counter

from shared.models import (
    RankRequest, RankResponse, ProductRecommendation, RejectedProduct,
)
from product_service.product_catalog import (
    PRODUCT_CATALOG, get_all_products, compute_efficacy_score,
    get_moa_group, TreatmentIntent, MOA_GROUPS,
)

logger = logging.getLogger(__name__)

MODEL_PATH = os.getenv("RANKER_MODEL_PATH", "ml/ranker_model.pkl")
MODEL_VERSION = "m8-hybrid-v1"

_model_cache = None


def _load_model():
    global _model_cache
    if _model_cache is not None:
        return _model_cache
    try:
        with open(MODEL_PATH, "rb") as f:
            _model_cache = pickle.load(f)
        logger.info("Loaded ranker model from %s", MODEL_PATH)
        return _model_cache
    except FileNotFoundError:
        logger.info("Ranker model not found — using efficacy-only mode.")
        return None
    except Exception as exc:
        logger.error("Failed to load ranker model: %s", exc)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# DYNAMIC WEIGHT COMPUTATION
# ══════════════════════════════════════════════════════════════════════════════

def _compute_weights(urgency: float) -> Tuple[float, float, float]:
    """
    Dynamic layer weights based on urgency.
    High urgency → efficacy dominates (farmer needs the RIGHT product NOW).
    Low urgency → adoption/affordability matter more (farmer has time to choose).
    """
    # Efficacy: 0.40 at low urgency → 0.60 at high urgency
    w_efficacy = 0.40 + 0.20 * urgency
    # Adoption: 0.30 at low urgency → 0.15 at high urgency
    w_adoption = 0.30 - 0.15 * urgency
    # Availability: 0.30 at low urgency → 0.25 at high urgency
    w_availability = 1.0 - w_efficacy - w_adoption
    return w_efficacy, w_adoption, w_availability


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 2: BEHAVIORAL ADOPTION
# ══════════════════════════════════════════════════════════════════════════════

def _adoption_score(product: str, crop: str, district: Optional[str], payload: dict) -> float:
    if payload is None:
        return 0.5
    crop_affinity = payload.get("crop_product_affinity", {}).get(crop, {}).get(product, 0.0)
    if district:
        dist_pop = payload.get("district_product_popularity", {}).get(district, {}).get(product, 0.0)
        return 0.65 * crop_affinity + 0.35 * dist_pop
    return crop_affinity


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 3: AVAILABILITY & AFFORDABILITY
# ══════════════════════════════════════════════════════════════════════════════

def _availability_score(product: str, district: Optional[str], payload: dict) -> float:
    if payload is None:
        return 0.5
    availability = payload.get("product_availability", {})
    if district:
        return availability.get(district, {}).get(product, 0.5)
    return availability.get("_global", {}).get(product, 0.5)


def _affordability_score(product: str, farm_size: Optional[float]) -> float:
    info = PRODUCT_CATALOG.get(product, {})
    tier = info.get("price_tier", "mid")
    if farm_size is None:
        return 0.7
    if farm_size < 2.0:
        return {"low": 1.0, "mid": 0.7, "premium": 0.4}[tier]
    elif farm_size > 8.0:
        return {"low": 0.6, "mid": 0.8, "premium": 1.0}[tier]
    return {"low": 0.8, "mid": 0.9, "premium": 0.7}[tier]


# ══════════════════════════════════════════════════════════════════════════════
# RESISTANCE MANAGEMENT — Spray History Memory
# ══════════════════════════════════════════════════════════════════════════════

def _compute_resistance_penalty(
    product: str,
    recently_used: Optional[List[str]],
    spray_history: Optional[List[str]],
) -> Tuple[float, Optional[str]]:
    """
    Penalize products whose MoA has been used recently.
    Returns (penalty_multiplier, reason_or_None).

    Penalty logic:
      - Same product used in last 14 days: 0.40× (severe)
      - Same MoA group used in last 14 days: 0.65× (moderate)
      - Same MoA used 3+ times this season: 0.50× (resistance risk)
    """
    product_moa = get_moa_group(product)
    if product_moa == "unknown":
        return 1.0, None

    # Check recent applications (last 14 days)
    if recently_used:
        if product in recently_used:
            return 0.40, f"Same product applied within 14 days (resistance risk)"

        recent_moa = {get_moa_group(p) for p in recently_used if get_moa_group(p) != "unknown"}
        if product_moa in recent_moa:
            return 0.65, f"Same MoA group ({product_moa}) used recently — rotate"

    # Check season-long history
    if spray_history:
        season_moa_counts = Counter(get_moa_group(p) for p in spray_history)
        if season_moa_counts.get(product_moa, 0) >= 3:
            return 0.50, f"MoA {product_moa} used {season_moa_counts[product_moa]}× this season — high resistance risk"

    return 1.0, None


def _generate_resistance_advisory(
    recently_used: Optional[List[str]],
    spray_history: Optional[List[str]],
) -> Optional[str]:
    """Generate a resistance management advisory based on spray history."""
    if not recently_used and not spray_history:
        return None

    all_products = (recently_used or []) + (spray_history or [])
    moa_counts = Counter(get_moa_group(p) for p in all_products if get_moa_group(p) != "unknown")

    if not moa_counts:
        return None

    most_common_moa, count = moa_counts.most_common(1)[0]
    if count >= 3:
        return (
            f"⚠️ Resistance advisory: MoA group {most_common_moa} has been used "
            f"{count}× this season. Rotate to a different mode of action to prevent "
            f"resistance buildup."
        )
    elif count >= 2:
        return (
            f"ℹ️ MoA group {most_common_moa} used {count}× — consider alternating "
            f"with a different resistance class for next application."
        )
    return None


# ══════════════════════════════════════════════════════════════════════════════
# CONTRAINDICATION CHECKS
# ══════════════════════════════════════════════════════════════════════════════

def _check_contraindications(product: str, request: RankRequest) -> Tuple[float, Optional[str]]:
    """
    Check for contraindications. Returns (penalty_multiplier, reason).
    """
    info = PRODUCT_CATALOG.get(product, {})

    # Pre-harvest interval: don't recommend sprays close to harvest
    if request.days_to_harvest is not None and request.days_to_harvest < 14:
        if info.get("application_mode") == "foliar":
            return 0.3, "Too close to harvest for foliar application (PHI concern)"

    # Seed treatments only at sowing
    if info.get("application_mode") == "seed":
        if request.crop_stage.value not in ("sowing", "general"):
            return 0.15, "Seed treatment not applicable at current growth stage"

    return 1.0, None


# ══════════════════════════════════════════════════════════════════════════════
# DIVERSITY ENFORCEMENT
# ══════════════════════════════════════════════════════════════════════════════

def _enforce_diversity(ranked: List[dict], top_k: int) -> List[dict]:
    """Ensure MoA diversity in top-k recommendations."""
    selected = []
    used_moa = set()

    for item in ranked:
        moa = item["moa_group"]
        if len(selected) == 0 or moa not in used_moa or moa == "unknown":
            selected.append(item)
            if moa != "unknown":
                used_moa.add(moa)
        if len(selected) >= top_k:
            break

    # Backfill if needed
    if len(selected) < top_k:
        for item in ranked:
            if item not in selected:
                selected.append(item)
            if len(selected) >= top_k:
                break

    return selected


# ══════════════════════════════════════════════════════════════════════════════
# "WHY NOT RECOMMENDED" LOGIC
# ══════════════════════════════════════════════════════════════════════════════

def _explain_rejections(
    all_scored: List[dict],
    selected_names: Set[str],
    request: RankRequest,
) -> List[RejectedProduct]:
    """
    For products that COULD have been recommended but weren't,
    explain why they were ranked lower.
    """
    rejections = []

    # Find products with decent efficacy that didn't make the cut
    for item in all_scored:
        if item["product_name"] in selected_names:
            continue
        if item["efficacy"] < 0.3:
            continue  # skip products that clearly don't match

        reasons = []

        # Check why it was rejected
        if item.get("resistance_reason"):
            reasons.append(item["resistance_reason"])

        if item.get("contraindication_reason"):
            reasons.append(item["contraindication_reason"])

        if item["availability"] < 0.3:
            reasons.append("Low stock availability in your district")

        info = PRODUCT_CATALOG.get(item["product_name"], {})
        if request.grower_farm_size and request.grower_farm_size < 2.0:
            if info.get("price_tier") == "premium":
                reasons.append("Premium pricing — may not suit small farm budget")

        # MoA diversity rejection
        if item.get("diversity_rejected"):
            reasons.append(f"Same MoA group ({item['moa_group']}) already represented in recommendations")

        if not reasons:
            reasons.append("Lower combined score than selected alternatives")

        rejections.append(RejectedProduct(
            product_name=item["product_name"],
            not_ranked_higher_because=reasons[:3],
        ))

        if len(rejections) >= 3:
            break

    return rejections


# ══════════════════════════════════════════════════════════════════════════════
# CONFIDENCE ESTIMATION
# ══════════════════════════════════════════════════════════════════════════════

def _compute_confidence(efficacy, adoption, availability, crop, pest, district, payload):
    conf = 0.0
    conf += 0.40 * min(efficacy / 0.8, 1.0)
    if payload is not None:
        crop_data = payload.get("crop_product_affinity", {}).get(crop, {})
        conf += 0.20 * (1.0 if len(crop_data) > 3 else 0.5)
    else:
        conf += 0.05
    if district and payload:
        dist_data = payload.get("district_product_popularity", {}).get(district, {})
        conf += 0.20 * (1.0 if len(dist_data) > 3 else 0.4)
    else:
        conf += 0.05
    conf += 0.20 * (1.0 if availability > 0.1 else 0.3)
    return min(conf, 1.0)


# ══════════════════════════════════════════════════════════════════════════════
# REASON GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def _generate_reasons(product, crop, pest, stage, urgency, efficacy, adoption,
                      avail, resistance_reason) -> List[str]:
    info = PRODUCT_CATALOG.get(product, {})
    reasons = []

    if crop.lower() in info.get("target_crops", set()):
        reasons.append(f"Registered for {crop} crop protection")
    if pest.lower() in info.get("target_pests", set()):
        reasons.append(f"Targets {pest} — efficacy rating {info['efficacy_rating']:.0%}")
    if stage.lower() in info.get("effective_stages", set()):
        reasons.append(f"Effective at {stage} growth stage")

    intents = info.get("treatment_intent", [])
    if urgency > 0.8 and TreatmentIntent.CURATIVE in intents:
        reasons.append("Curative action — suitable for high-urgency intervention")
    elif urgency > 0.8 and TreatmentIntent.RESCUE in intents:
        reasons.append("Rescue treatment — emergency intervention capability")
    elif urgency < 0.3 and TreatmentIntent.PREVENTIVE in intents:
        reasons.append("Preventive protection — ideal for proactive care")

    if info.get("systemic"):
        reasons.append("Systemic action — absorbed and translocated in plant")
    if adoption > 0.6:
        reasons.append("High regional adoption rate")
    if avail > 0.8:
        reasons.append("Good stock availability in your area")
    elif avail < 0.2:
        reasons.append("⚠️ Limited stock — check local retailer")
    if resistance_reason:
        reasons.append(f"⚠️ {resistance_reason}")

    return reasons[:5]


def _is_category_allowed(product_category: str, pest: str) -> bool:
    pest_lower = pest.lower()
    cat_lower = product_category.lower()
    
    if "weed" in pest_lower:
        return "herbicide" in cat_lower
    if any(x in pest_lower for x in ("aphid", "borer", "whitefly", "insect")):
        return "insecticide" in cat_lower or "seed_treatment" in cat_lower
    if any(x in pest_lower for x in ("rust", "blight", "wilt", "mildew", "fungal")):
        return "fungicide" in cat_lower or "seed_treatment" in cat_lower
        
    return True


# ══════════════════════════════════════════════════════════════════════════════
# MAIN RANKING FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def rank_products(request: RankRequest) -> RankResponse:
    """
    Main ranking function — adaptive agronomic decision engine.
    """
    payload = _load_model()
    all_products = get_all_products()

    # Dynamic weights based on urgency
    w_efficacy, w_adoption, w_availability = _compute_weights(request.urgency_score)

    # Score all products
    all_scored = []
    for product in all_products:
        # Check category alignment first to prevent leakage
        product_info = PRODUCT_CATALOG.get(product, {})
        category = product_info.get("category", "")
        if not _is_category_allowed(category, request.pest.value):
            continue

        # Layer 1: Efficacy
        efficacy = compute_efficacy_score(
            product, request.crop.value, request.pest.value,
            request.crop_stage.value, request.urgency_score
        )

        # Layer 2: Adoption
        adoption = _adoption_score(product, request.crop.value, request.district, payload)

        # Layer 3: Availability + affordability
        avail = _availability_score(product, request.district, payload)
        afford = _affordability_score(product, request.grower_farm_size)
        availability_combined = 0.7 * avail + 0.3 * afford

        # Combined base score
        combined = (
            w_efficacy * efficacy +
            w_adoption * adoption +
            w_availability * availability_combined
        )

        # Resistance penalty
        resistance_mult, resistance_reason = _compute_resistance_penalty(
            product, request.recently_used_products, request.spray_history
        )
        combined *= resistance_mult

        # Contraindication check
        contra_mult, contra_reason = _check_contraindications(product, request)
        combined *= contra_mult

        all_scored.append({
            "product_name": product,
            "combined_score": combined,
            "efficacy": round(efficacy, 3),
            "adoption": round(adoption, 3),
            "availability": round(availability_combined, 3),
            "moa_group": get_moa_group(product),
            "resistance_reason": resistance_reason,
            "contraindication_reason": contra_reason,
            "diversity_rejected": False,
        })

    # Sort by combined score
    all_scored.sort(key=lambda x: x["combined_score"], reverse=True)

    # Enforce diversity — mark rejected items
    selected = []
    used_moa = set()
    for item in all_scored:
        moa = item["moa_group"]
        if len(selected) == 0 or moa not in used_moa or moa == "unknown":
            selected.append(item)
            if moa != "unknown":
                used_moa.add(moa)
        else:
            item["diversity_rejected"] = True
        if len(selected) >= request.top_k:
            break

    # Backfill if needed
    if len(selected) < request.top_k:
        for item in all_scored:
            if item not in selected:
                selected.append(item)
            if len(selected) >= request.top_k:
                break

    # Build recommendations
    fallback_used = selected[0]["combined_score"] < 0.2 if selected else True
    selected_names = {item["product_name"] for item in selected}

    recommendations = []
    for item in selected:
        info = PRODUCT_CATALOG.get(item["product_name"], {})
        confidence = _compute_confidence(
            item["efficacy"], item["adoption"], item["availability"],
            request.crop.value, request.pest.value, request.district, payload
        )
        reasons = _generate_reasons(
            item["product_name"], request.crop.value, request.pest.value,
            request.crop_stage.value, request.urgency_score,
            item["efficacy"], item["adoption"], item["availability"],
            item["resistance_reason"]
        )
        recommendations.append(ProductRecommendation(
            product_name=item["product_name"],
            match_score=round(item["combined_score"], 3),
            confidence=round(confidence, 2),
            match_reasons=reasons,
            score_breakdown={
                "efficacy": item["efficacy"],
                "adoption": item["adoption"],
                "availability": item["availability"],
                "moa_group": item["moa_group"],
                "treatment_intent": [t for t in info.get("treatment_intent", [])],
                "price_tier": info.get("price_tier", "mid"),
                "weights_used": {
                    "efficacy": round(w_efficacy, 2),
                    "adoption": round(w_adoption, 2),
                    "availability": round(w_availability, 2),
                },
            },
        ))

    # "Why not recommended" explanations
    rejections = _explain_rejections(all_scored, selected_names, request)

    # Resistance advisory
    resistance_advisory = _generate_resistance_advisory(
        request.recently_used_products, request.spray_history
    )

    return RankResponse(
        grower_id=request.grower_id,
        crop=request.crop.value,
        pest=request.pest.value,
        top_products=recommendations,
        not_recommended=rejections if rejections else None,
        resistance_advisory=resistance_advisory,
        fallback_used=fallback_used,
        model_version=MODEL_VERSION,
    )
