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

from .models import FarmerContext, UrgencyResponse
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
        logger.exception("Scoring failed for grower %s", ctx.grower_id)
        raise HTTPException(status_code=500, detail=str(exc))


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
        logger.exception("SHAP explanation failed for grower %s", ctx.grower_id)
        raise HTTPException(status_code=500, detail=str(exc))
