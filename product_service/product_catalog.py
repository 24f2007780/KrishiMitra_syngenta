"""
M8 Product Ranker — Dynamic DB-backed Product Knowledge Base + Agronomic Ontology
Syngenta IITM Hackathon 2026
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)
_REPO_ROOT = Path(__file__).resolve().parents[1]
_CANONICAL_JSON = _REPO_ROOT / "product-catalog" / "canonical_products.json"

# Ensure parent directory is in sys.path to resolve imports from app and shared
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.database import SessionLocal
from shared.models import Product

# ══════════════════════════════════════════════════════════════════════════════
# TREATMENT INTENT CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════════
class TreatmentIntent:
    PREVENTIVE = "preventive"       # Apply before symptoms appear
    CURATIVE = "curative"           # Apply after early symptoms
    RESCUE = "rescue"               # Emergency high-dose intervention
    SEED_TREATMENT = "seed_treatment"  # Pre-sowing protection


PRODUCT_CATALOG: Dict[str, dict] = {}
MOA_GROUPS: Dict[str, dict] = {}


def _ingest_row(
    name: str,
    *,
    category: str,
    active_ingredient: str,
    target_crop: str,
    target_pest: str,
    effective_stages: str,
    treatment_intent: str,
    efficacy_rating: float,
    price_tier: str,
    application_mode: str,
    systemic: bool,
    rain_sensitive_hours: int,
    description: str,
    moa_group: str | None = None,
    moa_class: str | None = None,
) -> None:
    target_crops = {c.strip().lower() for c in (target_crop or "").split(",") if c.strip()}
    target_pests = {pt.strip().lower() for pt in (target_pest or "").split(",") if pt.strip()}
    stages = {s.strip().lower() for s in (effective_stages or "general").split(",") if s.strip()}
    intents = [ti.strip().lower() for ti in (treatment_intent or "").split(",") if ti.strip()]

    PRODUCT_CATALOG[name] = {
        "category": category or "fungicide",
        "active_ingredient": active_ingredient or "",
        "target_pests": target_pests,
        "target_crops": target_crops,
        "effective_stages": stages,
        "treatment_intent": intents,
        "efficacy_rating": efficacy_rating if efficacy_rating is not None else 0.8,
        "price_tier": price_tier or "mid",
        "application_mode": application_mode or "foliar",
        "systemic": bool(systemic),
        "rain_sensitive_hours": rain_sensitive_hours or 0,
        "description": description or "",
    }
    if moa_group:
        MOA_GROUPS[name] = {"group": moa_group, "class": moa_class or ""}


def load_catalog_from_json(path: Path | None = None) -> int:
    """Load catalog from canonical_products.json (fallback when DB is empty)."""
    global PRODUCT_CATALOG, MOA_GROUPS
    PRODUCT_CATALOG.clear()
    MOA_GROUPS.clear()

    json_path = path or _CANONICAL_JSON
    if not json_path.is_file():
        logger.warning("Product catalog JSON not found: %s", json_path)
        return 0

    with open(json_path, encoding="utf-8") as f:
        items: List[Dict[str, Any]] = json.load(f)

    for item in items:
        name = item.get("name")
        if not name:
            continue
        _ingest_row(
            name,
            category=item.get("type") or "fungicide",
            active_ingredient=item.get("active_ingredients") or "",
            target_crop=item.get("target_crop") or "",
            target_pest=item.get("target_pest") or "",
            effective_stages=item.get("effective_stages") or "general",
            treatment_intent=item.get("treatment_intent") or "",
            efficacy_rating=float(item.get("efficacy_rating") or 0.8),
            price_tier=item.get("price_tier") or "mid",
            application_mode=item.get("application_mode") or "foliar",
            systemic=bool(item.get("systemic")),
            rain_sensitive_hours=int(item.get("rain_sensitive_hours") or 0),
            description=item.get("description") or "",
            moa_group=item.get("moa_group"),
            moa_class=item.get("moa_class"),
        )

    logger.info("Loaded %d products from %s", len(PRODUCT_CATALOG), json_path.name)
    return len(PRODUCT_CATALOG)


def load_catalog_from_db() -> int:
    global PRODUCT_CATALOG, MOA_GROUPS
    PRODUCT_CATALOG.clear()
    MOA_GROUPS.clear()
    try:
        db = SessionLocal()
        db_products = db.query(Product).all()
        db.close()

        if not db_products:
            raise ValueError("No products found in database.")

        for p in db_products:
            _ingest_row(
                p.name,
                category=p.type or "fungicide",
                active_ingredient=p.active_ingredients or "",
                target_crop=p.target_crop or "",
                target_pest=p.target_pest or "",
                effective_stages=p.effective_stages or "general",
                treatment_intent=p.treatment_intent or "",
                efficacy_rating=p.efficacy_rating if p.efficacy_rating is not None else 0.8,
                price_tier=p.price_tier or "mid",
                application_mode=p.application_mode or "foliar",
                systemic=bool(p.systemic),
                rain_sensitive_hours=p.rain_sensitive_hours or 0,
                description=p.description or "",
                moa_group=p.moa_group,
                moa_class=p.moa_class,
            )

        logger.info("Loaded %d products from database", len(PRODUCT_CATALOG))
        return len(PRODUCT_CATALOG)
    except Exception as e:
        logger.warning("DB catalog load failed (%s); trying JSON fallback", e)
        return load_catalog_from_json()


def ensure_catalog_loaded() -> int:
    """DB first; JSON fallback. Call after init_db/seed on startup."""
    n = load_catalog_from_db()
    if n == 0:
        n = load_catalog_from_json()
    if n == 0:
        logger.error("Product catalog is empty — run: python -m app.seeder")
    return n


reload_catalog = ensure_catalog_loaded

# ══════════════════════════════════════════════════════════════════════════════
# QUERY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def get_all_products() -> List[str]:
    return list(PRODUCT_CATALOG.keys())


def get_products_for_crop(crop: str) -> List[str]:
    return [n for n, i in PRODUCT_CATALOG.items() if any(crop.lower() in c for c in i["target_crops"])]


def get_products_for_pest(pest: str) -> List[str]:
    return [n for n, i in PRODUCT_CATALOG.items() if any(pest.lower() in p for p in i["target_pests"])]


def compute_efficacy_score(product_name: str, crop: str, pest: str, stage: str,
                           urgency: float) -> float:
    """
    Agronomic EFFICACY score — how well this product treats the problem.
    Separate from popularity. Based on domain knowledge.
    """
    info = PRODUCT_CATALOG.get(product_name)
    if info is None:
        return 0.0

    score = 0.0

    # Crop match (25%)
    if any(crop.lower() in c for c in info["target_crops"]):
        score += 0.25

    # Pest match (30%) — strongest efficacy signal
    if any(pest.lower() in p for p in info["target_pests"]):
        score += 0.30
    elif pest == "general":
        score += 0.10

    # Stage match (15%)
    if any(stage.lower() in s for s in info["effective_stages"]) or "general" in info["effective_stages"]:
        score += 0.15

    # Base efficacy rating (20%)
    score += 0.20 * info["efficacy_rating"]

    # Treatment intent alignment with urgency (10%)
    intents = info["treatment_intent"]
    if urgency > 0.8:
        # High urgency → prefer curative/rescue
        if TreatmentIntent.RESCUE in intents or TreatmentIntent.CURATIVE in intents:
            score += 0.10
    elif urgency < 0.3:
        # Low urgency → prefer preventive/seed treatment
        if TreatmentIntent.PREVENTIVE in intents or TreatmentIntent.SEED_TREATMENT in intents:
            score += 0.10
    else:
        score += 0.05  # neutral

    return min(score, 1.0)


def get_moa_group(product_name: str) -> str:
    """Get the Mode of Action group for resistance management."""
    return MOA_GROUPS.get(product_name, {}).get("group", "unknown")

# Best-effort load at import; startup hook re-runs after DB seed
ensure_catalog_loaded()
