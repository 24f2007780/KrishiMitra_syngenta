"""
M8 Product Ranker — FastAPI Application
Syngenta IITM Hackathon 2026

POST /rank → Top-k product recommendations with match reasoning
"""

from fastapi import FastAPI, HTTPException
import logging

from shared.models import RankRequest, RankResponse, FarmerContext, CropType, PestType, CropStage
from product_service.ranker import rank_products

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="M8 Product Ranker",
    description=(
        "Hybrid product recommendation engine. "
        "Rule-based crop-pest matching + ML collaborative filtering "
        "from POS purchase patterns + availability-aware ranking."
    ),
    version="1.0.0",
)


@app.on_event("startup")
def startup_load_catalog():
    """Create tables and seed products if DB is empty, then reload ranker catalog."""
    from app.database import SessionLocal, init_db
    from app.seeder import seed_products
    from product_service.product_catalog import ensure_catalog_loaded
    from shared.models import Product

    init_db()
    db = SessionLocal()
    try:
        if db.query(Product).count() == 0:
            logger.info("Products table empty — seeding from canonical_products.json")
            seed_products(db)
    finally:
        db.close()
    ensure_catalog_loaded()


@app.get("/health")
def health():
    from product_service.product_catalog import PRODUCT_CATALOG

    return {
        "status": "ok",
        "engine": "m8-hybrid-v1",
        "catalog_size": len(PRODUCT_CATALOG),
    }


@app.post("/rank", response_model=RankResponse)
def rank(context: FarmerContext):
    """
    **POST /rank**

    Returns top-k product recommendations for a given farmer context.
    Takes a FarmerContext as the request body.
    """
    try:
        # Build RankRequest from FarmerContext
        crop_str = context.profile.crops[0] if context.profile.crops else "wheat"
        pest_str = context.signals.active_pest if context.signals.active_pest != "None" else "rust"
        stage_str = context.crop_stage.confirmed_stage if context.crop_stage.confirmed_stage else "general"
        
        crop_enum = next((c for c in CropType if c.value == crop_str.lower()), CropType.wheat)
        pest_enum = next((p for p in PestType if p.value in pest_str.lower()), PestType.general)
        stage_enum = next((s for s in CropStage if s.value == stage_str.lower()), CropStage.general)
        
        import sys
        sys.path.insert(0, ".")
        from urgency_scorer.scorer import compute_urgency

        # Determine urgency score using urgency scorer (M7)
        try:
            urgency_res = compute_urgency(context)
            urgency = urgency_res.urgency_score
        except Exception as exc:
            logger.warning(f"Failed to compute dynamic urgency, falling back to heuristic: {exc}")
            if hasattr(context.signals, 'pest_risk') and isinstance(context.signals.pest_risk, (int, float)):
                urgency = float(context.signals.pest_risk)
            elif hasattr(context.signals, 'pest_risk_level') and context.signals.pest_risk_level:
                risk = context.signals.pest_risk_level.lower()
                if risk == "high":
                    urgency = 0.8
                elif risk == "medium":
                    urgency = 0.5
                else:
                    urgency = 0.2
            else:
                urgency = 0.2
            
        request = RankRequest(
            grower_id=context.profile.grower_id,
            crop=crop_enum,
            pest=pest_enum,
            crop_stage=stage_enum,
            urgency_score=urgency,
            district=context.profile.district,
            grower_farm_size=context.profile.grower_farm_size,
            top_k=3
        )
        
        return rank_products(request)
    except Exception as exc:
        logger.exception("Ranking failed")
        raise HTTPException(status_code=500, detail=str(exc))

import httpx

@app.get("/products/{grower_id}", response_model=RankResponse)
async def get_products(grower_id: str):
    """
    Call GET /products/{grower_id}
    Fetches the context from M6 and returns top products matching the farmer's pest risk and crop stage.
    """
    try:
        # Fetch farmer context from context_service (M6)
        async with httpx.AsyncClient() as client:
            context_res = await client.get(f"http://localhost:8006/context/{grower_id}")
            if context_res.status_code != 200:
                raise HTTPException(status_code=context_res.status_code, detail=f"Failed to fetch context: {context_res.text}")
            
            context_data = context_res.json()
            context = FarmerContext(**context_data)
            
        # Use the same logic as /rank
        return rank(context)
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"GET /products failed for {grower_id}")
        raise HTTPException(status_code=500, detail=str(exc))
