"""
M7 Intelligence Engine — FastAPI Application
Syngenta IITM Hackathon 2026

Endpoints:
  POST /score    →  Full 3-layer scoring (urgency + engagement + priority)
  POST /explain  →  HTML SHAP waterfall explanation
  GET  /health   →  Service health check
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import logging
import httpx
import json
from datetime import datetime, date

from shared.models import (
    FarmerContext, UrgencyResponse, Farmer, FarmerProfile,
    SignalBundle, FarmerStage
)
from app.database import SessionLocal
from .scorer import compute_urgency
from .shap_explainer import generate_shap_html

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="M7 Intelligence Engine",
    description=(
        "Domain-informed urgency intelligence engine with adaptive ML enrichment. "
        "Prioritizes farmer interventions using agronomic risk and behavioral responsiveness. "
        "Handles cold-start gracefully via population priors."
    ),
    version="2.0.0",
)


@app.get("/health")
def health():
    return {"status": "ok", "engine": "m7-hybrid-v2"}


@app.post("/score", response_model=UrgencyResponse)
def score(ctx: FarmerContext):
    """
    **POST /score** — M7 Hybrid Intelligence Engine

    **3-Layer Architecture:**

    1. **Agronomic Urgency** (rule-based, deterministic):
       `urgency = 0.40×pest_risk + 0.30×weather_anomaly + 0.20×crop_vulnerability + 0.10×(1−recency_penalty)`

    2. **Behavioral Engagement** (ML or cold-start priors):
       Predicts click likelihood from behavioral signals.
       New farmers use district/crop/device population priors.

    3. **Delivery Intelligence** (fusion + suppression):
       `priority = 0.65×urgency + 0.35×engagement`
       Applies fatigue guard and recommends optimal channel.
    """
    try:
        result = compute_urgency(ctx)
        return result
    except Exception as exc:
        logger.exception("Scoring failed for grower %s", ctx.profile.grower_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/score/{grower_id}", response_model=UrgencyResponse)
def score_by_grower_id(grower_id: str):
    """
    **GET /score/{grower_id}** — M7 Urgency Scorer by Grower ID

    Fetches farmer from master.db, retrieves weather signals from weather service (M4),
    and parses grower_crop_calendar for growth stage susceptibility.
    """ 
    db = SessionLocal()
    try:
        farmer = db.query(Farmer).filter(Farmer.grower_id == grower_id).first()
        if not farmer:
            raise HTTPException(status_code=404, detail="Farmer not found")

        # Map crops
        crops_list = [c.strip() for c in farmer.crops.split(",")] if farmer.crops else ["wheat"]

        # Build FarmerProfile Pydantic model
        profile = FarmerProfile(
            grower_id=farmer.grower_id,
            name=farmer.name or "Unknown",
            grower_age=farmer.grower_age or farmer.age or 40,
            phone=farmer.phone or "",
            preferred_language=farmer.preferred_language or "Hindi",
            state=farmer.state or "Rajasthan",
            district=farmer.district or "",
            tehsil=farmer.tehsil or "",
            grower_farm_size=farmer.grower_farm_size or 2.0,
            crops=crops_list,
            latitude=farmer.latitude or 27.0,
            longitude=farmer.longitude or 74.0,
            device_type=farmer.device_type or "smartphone",
            connectivity=farmer.connectivity or "4G",
            whatsapp_enabled=farmer.whatsapp_enabled or True,
            last_message_sent_at=farmer.last_message_sent_at,
            messages_received_last_30d=farmer.messages_received_last_30d or 0,
            messages_opened_last_30d=farmer.messages_opened_last_30d or 0,
            preferred_contact_time=farmer.preferred_contact_time or "morning",
            linked_retailer_id=farmer.linked_retailer_id or "",
            linked_retailer_name=farmer.linked_retailer_name or "",
            urgency_score=farmer.urgency_score or 0.0,
            recommended_channel=farmer.recommended_channel
        )

        # Call Weather Service (M4) to get SignalBundle
        signals = None
        try:
            with httpx.Client(timeout=3.0) as client:
                w_res = client.get(
                    "http://localhost:8004/signals/weather",
                    params={"lat": farmer.latitude or 27.0238, "lon": farmer.longitude or 74.2179}
                )
                if w_res.status_code == 200:
                    signals = SignalBundle(**w_res.json())
        except Exception as e:
            logger.warning(f"Failed to fetch weather signals from M4: {e}")

        # Fallback signals if API call fails
        if not signals:
            signals = SignalBundle(
                district=farmer.district or "",
                state=farmer.state or "",
                humidity_7d_avg=60.0,
                rainfall_deviation_pct=0.0,
                weather_anomaly=0.2,
                pest_risk=0.3,
                active_pest="None",
                weather_anomaly_flag=False
            )

        # Parse grower_crop_calendar for FarmerStage
        crop_stage = None
        if farmer.grower_crop_calendar:
            try:
                cal = json.loads(farmer.grower_crop_calendar)
                target_date = date.today()

                confirmed_stage = "vegetative"
                vuln = 0.5
                days_to_next = 30

                sowing_start = date.fromisoformat(cal["sowing"]["start"])
                sowing_end = date.fromisoformat(cal["sowing"]["end"])
                harvest_start = date.fromisoformat(cal["harvest"]["start"])
                harvest_end = date.fromisoformat(cal["harvest"]["end"])

                stages = []
                for s in cal.get("stages", []):
                    stages.append({
                        "stage": s["stage"],
                        "approx": date.fromisoformat(s["approx"])
                    })
                stages.sort(key=lambda x: x["approx"])

                if target_date < sowing_start:
                    confirmed_stage = "fallow"
                    days_to_next = (sowing_start - target_date).days
                    vuln = 0.2
                elif sowing_start <= target_date <= sowing_end:
                    confirmed_stage = "sowing"
                    days_to_next = (sowing_end - target_date).days
                    vuln = 0.8
                elif target_date > harvest_end:
                    confirmed_stage = "fallow"
                    days_to_next = 180
                    vuln = 0.2
                elif harvest_start <= target_date <= harvest_end:
                    confirmed_stage = "harvest"
                    days_to_next = (harvest_end - target_date).days
                    vuln = 0.2
                else:
                    confirmed_stage = "vegetative"
                    next_stage_date = harvest_start

                    for stage in stages:
                        approx = stage["approx"]
                        if target_date >= approx:
                            confirmed_stage = stage["stage"]
                        else:
                            next_stage_date = approx
                            break

                    days_to_next = (next_stage_date - target_date).days
                    vuln_map = {
                        "sowing": 0.8,
                        "tillering": 0.5,
                        "flowering": 0.8,
                        "vegetative": 0.5,
                        "harvest": 0.2,
                        "fallow": 0.2
                    }
                    vuln = vuln_map.get(confirmed_stage.lower(), 0.5)

                crop_stage = FarmerStage(
                    confirmed_stage=confirmed_stage,
                    days_in_stage=0,
                    crop_vulnerability=vuln,
                    days_to_next_stage=days_to_next
                )
            except Exception as parse_err:
                logger.warning(f"Error parsing crop calendar: {parse_err}")

        # Fallback FarmerStage
        if not crop_stage:
            crop_stage = FarmerStage(
                confirmed_stage="vegetative",
                days_in_stage=0,
                crop_vulnerability=0.5,
                days_to_next_stage=30
            )

        ctx = FarmerContext(
            profile=profile,
            signals=signals,
            crop_stage=crop_stage,
            assembled_at=datetime.now().isoformat()
        )

        return compute_urgency(ctx)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(f"Prediction failed for grower {grower_id}")
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()


@app.post("/explain", response_class=HTMLResponse)
def explain(ctx: FarmerContext):
    """
    **POST /explain**

    Returns a standalone HTML page with SHAP-style waterfall chart
    explaining how each feature contributed to the urgency and engagement scores.
    """
    try:
        html = generate_shap_html(ctx)
        return HTMLResponse(content=html)
    except Exception as exc:
        logger.exception("SHAP explanation failed for grower %s", ctx.profile.grower_id)
        raise HTTPException(status_code=500, detail=str(exc))
