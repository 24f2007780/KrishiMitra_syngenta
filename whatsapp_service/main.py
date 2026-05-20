"""M11 — KrishiMitra WhatsApp service: send advisory messages from farmer context."""

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

from sms_service.context import build_whatsapp_body  # noqa: E402
from whatsapp_service.send import send_farmer_whatsapp  # noqa: E402

app = FastAPI(title="KrishiMitra WhatsApp (M11)", version="0.2.0")


class FarmerWhatsAppRequest(BaseModel):
    """Same farmer context fields as voice / SMS."""

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
    sms_script: Optional[str] = None
    whatsapp_script: Optional[str] = Field(
        None,
        description="Exact WhatsApp text. Falls back to sms_script / intro_script.",
    )
    whatsapp_body: Optional[str] = Field(None, description="Alias for whatsapp_script")
    dry_run: bool = False
    max_length: int = Field(4096, ge=50, le=16000)
    connect_timeout: float = Field(180, ge=30, le=600)


@app.get("/health")
def health():
    session_dir = _ROOT / "whatsapp_apps" / "web" / "sessions"
    return {
        "status": "ok",
        "module": "M11",
        "service": "krishimitra_whatsapp",
        "session_dir": str(session_dir),
        "session_exists": any(session_dir.glob("*.sqlite3")),
    }


@app.post("/whatsapp/preview")
def preview_whatsapp(body: FarmerWhatsAppRequest):
    """Return the message that would be sent (no WhatsApp call)."""
    ctx = body.model_dump(
        exclude={"dry_run", "max_length", "connect_timeout"},
    )
    text = build_whatsapp_body(ctx, max_length=body.max_length)
    return {"to_number": body.to_number, "body": text, "length": len(text)}


@app.post("/whatsapp/send")
def send_whatsapp_endpoint(body: FarmerWhatsAppRequest):
    """Send advisory WhatsApp using farmer context."""
    ctx = body.model_dump(
        exclude={"dry_run", "max_length", "connect_timeout"},
    )
    try:
        out = send_farmer_whatsapp(
            ctx,
            dry_run=body.dry_run,
            max_length=body.max_length,
            connect_timeout=body.connect_timeout,
        )
        return {"success": True, **out}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("M11_PORT", "8011")))
