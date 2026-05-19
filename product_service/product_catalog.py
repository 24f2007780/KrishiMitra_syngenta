"""
M8 Product Ranker — Dynamic DB-backed Product Knowledge Base + Agronomic Ontology
Syngenta IITM Hackathon 2026
"""

import os
import sys
from typing import Dict, List, Set

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

def load_catalog_from_db():
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
            # Parse target_crops and target_pests (ensure case-insensitive lower case comparison keys)
            target_crops = {c.strip().lower() for c in (p.target_crop or "").split(",") if c.strip()}
            target_pests = {pt.strip().lower() for pt in (p.target_pest or "").split(",") if pt.strip()}
            effective_stages = {s.strip().lower() for s in (p.effective_stages or "general").split(",") if s.strip()}
            treatment_intents = [ti.strip().lower() for ti in (p.treatment_intent or "").split(",") if ti.strip()]
            
            PRODUCT_CATALOG[p.name] = {
                "category": p.type or "fungicide",
                "active_ingredient": p.active_ingredients or "",
                "target_pests": target_pests,
                "target_crops": target_crops,
                "effective_stages": effective_stages,
                "treatment_intent": treatment_intents,
                "efficacy_rating": p.efficacy_rating if p.efficacy_rating is not None else 0.8,
                "price_tier": p.price_tier or "mid",
                "application_mode": p.application_mode or "foliar",
                "systemic": bool(p.systemic),
                "rain_sensitive_hours": p.rain_sensitive_hours if p.rain_sensitive_hours is not None else 0,
                "description": p.description or "",
            }
            
            if p.moa_group:
                MOA_GROUPS[p.name] = {
                    "group": p.moa_group,
                    "class": p.moa_class or ""
                }
    except Exception as e:
        import logging
        logging.error(f"Failed to load product catalog from DB: {e}")

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

# Initialize load immediately
load_catalog_from_db()
