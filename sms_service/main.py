"""M10 — KrishiMitra SMS service: send advisory SMS from farmer context."""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_ROOT / ".env")

from sms_service.context import build_sms_body  # noqa: E402
from sms_service.send import send_farmer_sms  # noqa: E402

app = FastAPI(title="KrishiMitra SMS (M10)", version="0.2.0")


class FarmerSmsRequest(BaseModel):
    """Same farmer context fields as twilio-voice-agent ``/krishimitra/call``."""

    to_number: str = Field(..., description="E.164, e.g. +919152155576")
    farmer_id: Optional[str] = None
    farmer_name: str = "Farmer"
    preferred_language: str = "English"
    state: Optional[str] = None
    district: Optional[str] = None
    village: Optional[str] = None
    crops: List[str] = Field(default_factory=list)
    crop: Optional[str] = None
    crop_stage: Optional[str] = None
    pest_risk_level: Optional[str] = None
    active_pest: Optional[str] = None
    why_now: Optional[str] = None
    recommended_product: Optional[str] = None
    retailer_name: Optional[str] = None
    urgency_score: Optional[float] = None
    intro_script: Optional[str] = None
    example_message_en: Optional[str] = None
    sms_script: Optional[str] = Field(
        None,
        description="Exact SMS text. Overrides example_message_en if set.",
    )
    sms_body: Optional[str] = Field(None, description="Alias for sms_script")
    dry_run: bool = False
    max_length: int = Field(320, ge=50, le=1600)


@app.get("/health")
def health():
    twilio_ok = bool(
        os.environ.get("TWILIO_ACCOUNT_SID")
        and os.environ.get("TWILIO_AUTH_TOKEN")
        and (os.environ.get("TWILIO_PHONE_NUMBER") or os.environ.get("TWILIO_SMS_FROM"))
    )
    return {
        "status": "ok",
        "module": "M10",
        "service": "krishimitra_sms",
        "twilio_configured": twilio_ok,
    }


@app.post("/sms/preview")
def preview_sms(body: FarmerSmsRequest):
    """Return the SMS text that would be sent (no Twilio call)."""
    ctx = body.model_dump(exclude={"dry_run", "max_length"})
    text = build_sms_body(ctx, max_length=body.max_length)
    return {"to_number": body.to_number, "body": text, "length": len(text)}


@app.post("/sms/send")
def send_sms_endpoint(body: FarmerSmsRequest):
    """Send advisory SMS using farmer context."""
    ctx = body.model_dump(exclude={"dry_run", "max_length"})
    try:
        out = send_farmer_sms(
            ctx,
            dry_run=body.dry_run,
            max_length=body.max_length,
        )
        return {"success": True, **out}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("M10_PORT", "8010")))
