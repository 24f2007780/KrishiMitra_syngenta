"""KrishiMitra API routes — outbound voice calls with farmer context."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from krishimitra.context import build_system_instruction, load_base_persona
from krishimitra.store import put

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/krishimitra", tags=["krishimitra"])

# Set from app.py on startup
twilio_client = None
PHONE_NO: str = ""
TUNNEL_LINK: str = ""


def configure_twilio(client, phone_no: str, tunnel_link: str) -> None:
    global twilio_client, PHONE_NO, TUNNEL_LINK
    twilio_client = client
    PHONE_NO = phone_no
    TUNNEL_LINK = tunnel_link


class FarmerVoiceCallRequest(BaseModel):
    """Place an outbound advisory call with personalised context."""

    to_number: str = Field(..., description="E.164, e.g. +919471961925")
    farmer_id: Optional[str] = None
    farmer_name: str = "Rajan Kumar"
    preferred_language: str = "Tamil"
    state: str = "Tamil Nadu"
    district: str = "Thanjavur"
    village: Optional[str] = None
    crops: List[str] = Field(default_factory=lambda: ["rice"])
    crop_stage: str = "flowering"
    pest_risk_level: str = "high"
    active_pest: Optional[str] = "fungal"
    why_now: str = "High humidity for several days; fungal risk on flowering rice."
    recommended_product: str = "Amistar"
    retailer_name: str = "Suresh Agro Stores"
    urgency_score: Optional[float] = 0.84
    intro_script: Optional[str] = Field(
        None,
        description="Exact words for phone opening (Hindi/Bhojpuri). If omitted, auto-generated from context.",
    )


@router.get("/health")
def krishimitra_health():
    return {
        "status": "ok",
        "service": "krishimitra_voice",
        "tunnel_configured": bool(TUNNEL_LINK),
        "twilio_configured": bool(twilio_client and PHONE_NO),
    }


@router.post("/call")
async def place_farmer_call(body: FarmerVoiceCallRequest):
    """Dial farmer; Twilio connects Media Stream to Gemini with this context."""
    if not twilio_client or not PHONE_NO:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Twilio not configured (TWILIO_ACCOUNT_SID, TWILIO_PHONE_NUMBER)"},
        )
    if not TUNNEL_LINK:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "TUNNEL_LINK / NGROK_PUBLIC_URL not set"},
        )

    context_id = str(uuid.uuid4())
    ctx: Dict[str, Any] = body.model_dump()
    ctx["crop"] = body.crops[0] if body.crops else "rice"
    put(context_id, ctx)

    voice_url = f"{TUNNEL_LINK.rstrip('/')}/twilio/voice?context_id={context_id}"
    try:
        call = twilio_client.calls.create(
            to=body.to_number,
            from_=PHONE_NO,
            url=voice_url,
            method="GET",
            status_callback=f"{TUNNEL_LINK.rstrip('/')}/twilio/status",
            status_callback_event=["initiated", "ringing", "answered", "completed", "failed"],
        )
    except Exception as e:
        logger.exception("KrishiMitra call failed")
        return JSONResponse(status_code=400, content={"success": False, "error": str(e)})

    return JSONResponse(
        content={
            "success": True,
            "call_sid": call.sid,
            "context_id": context_id,
            "voice_url": voice_url,
            "message": f"Calling {body.to_number} as KrishiMitra advisory",
        }
    )


@router.post("/preview-instruction")
async def preview_instruction(body: FarmerVoiceCallRequest):
    """Debug: see the system prompt that would be sent to Gemini."""
    ctx = body.model_dump()
    ctx["crop"] = body.crops[0] if body.crops else "rice"
    return {
        "persona_chars": len(load_base_persona()),
        "full_instruction": build_system_instruction(ctx),
    }
