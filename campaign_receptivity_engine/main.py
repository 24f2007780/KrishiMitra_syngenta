"""
Campaign Receptivity Engine — FastAPI Application
Syngenta IITM Hackathon 2026

POST /predict → Campaign receptivity + format recommendations
POST /explain → Detailed HTML SHAP explanation
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import logging

from shared.models import (
    ReceptivityRequest, ReceptivityResponse, Farmer,
    WhatsAppCampaign, CropType, DeviceType
)
from app.database import SessionLocal
from .predictor import predict_receptivity
from .shap_explainer import generate_shap_html
from datetime import date

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Campaign Receptivity Engine",
    description=(
        "Predicts campaign receptivity and recommends optimal creative formats. "
        "Segments farmers by engagement behavior and predicts which approaches "
        "drive highest engagement for each segment. "
        "Includes SHAP-based HTML explainability."
    ),
    version="1.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "engine": "campaign-receptivity-v1"}


@app.post("/predict", response_model=ReceptivityResponse)
def predict(request: ReceptivityRequest):
    """
    **POST /predict** — Campaign Receptivity Prediction

    Returns:
    - Farmer segment classification
    - Overall receptivity score
    - Ranked format recommendations
    - Timing intelligence
    - Fatigue risk assessment
    - Creative strategy suggestions
    """
    try:
        return predict_receptivity(request)
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/predict/{grower_id}", response_model=ReceptivityResponse)
def predict_by_grower_id(grower_id: str):
    """
    **GET /predict/{grower_id}** — Campaign Receptivity Prediction by Grower ID

    Fetches farmer profile and campaign history from the database to predict receptivity.
    """
    db = SessionLocal()
    try:
        farmer = db.query(Farmer).filter(Farmer.grower_id == grower_id).first()
        if not farmer:
            raise HTTPException(status_code=404, detail="Farmer not found")

        # Calculate click and open rates from campaign history
        campaigns = db.query(WhatsAppCampaign).filter(WhatsAppCampaign.grower_id == grower_id).all()
        total_campaigns = len(campaigns)

        if total_campaigns > 0:
            clicked_count = sum(1 for c in campaigns if c.clicked_status)
            opened_count = sum(1 for c in campaigns if c.opened_status)
            historical_click_rate = clicked_count / total_campaigns
            historical_open_rate = opened_count / total_campaigns
            previously_clicked = clicked_count > 0
            latest_campaign = sorted(campaigns, key=lambda c: c.message_sent_date or "", reverse=True)[0]
            campaign_product = latest_campaign.campaign_product
        else:
            historical_click_rate = 0.0
            # Fallback to profile stats
            if farmer.messages_received_last_30d and farmer.messages_received_last_30d > 0:
                historical_open_rate = (farmer.messages_opened_last_30d or 0) / farmer.messages_received_last_30d
            else:
                historical_open_rate = 0.0
            previously_clicked = False
            campaign_product = farmer.product_name

        # Map crop
        crop_str = farmer.crops.split(",")[0].strip().lower() if farmer.crops else "wheat"
        crop_enum = next((c for c in CropType if c.value == crop_str), CropType.wheat)

        # Map device
        device_str = (farmer.device_type or "unknown").lower().strip()
        device_enum = next((d for d in DeviceType if d.value == device_str), DeviceType.unknown)

        request = ReceptivityRequest(
            grower_id=farmer.grower_id,
            crop=crop_enum,
            district=farmer.district,
            device_type=device_enum,
            farm_size_acres=farmer.grower_farm_size,
            grower_age=farmer.grower_age,
            campaign_product=campaign_product,
            scoring_date=date.today(),
            historical_open_rate=historical_open_rate,
            historical_click_rate=historical_click_rate,
            messages_received_last_30d=farmer.messages_received_last_30d,
            previously_clicked=previously_clicked,
            product_scanned=farmer.product_scan,
            offline_campaign_attended=farmer.offline_campaign_attended,
        )

        return predict_receptivity(request)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Prediction failed for grower {grower_id}")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()


@app.post("/explain", response_class=HTMLResponse)
def explain(request: ReceptivityRequest):
    """
    **POST /explain** — Detailed SHAP Explanation

    Returns a standalone HTML page with:
    - SHAP waterfall chart showing feature contributions
    - Segment classification reasoning
    - Format recommendation rationale
    - Fatigue risk decomposition
    - Timing and creative strategy explanations
    """
    try:
        html = generate_shap_html(request)
        return HTMLResponse(content=html)
    except Exception as exc:
        logger.exception("SHAP explanation failed")
        raise HTTPException(status_code=500, detail=str(exc))
