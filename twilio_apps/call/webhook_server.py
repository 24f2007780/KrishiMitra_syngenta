"""
FastAPI app Twilio calls for voice: opening TwiML + speech Gather + LLM reply.

Loads .env from repo root. Session IDs are in the **URL path** so Twilio POST
requests always hit the right session (query strings are unreliable on POST).
"""

from __future__ import annotations

import logging
import traceback
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Form, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from starlette.requests import Request as StarletteRequest
from xml.sax.saxutils import escape

from twilio.twiml.voice_response import Gather, VoiceResponse

_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")

from twilio_apps.call import reply as reply_mod  # noqa: E402
from twilio_apps.call import session_store  # noqa: E402
from twilio_apps.call.env_urls import voice_public_base_url  # noqa: E402

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("twilio_voice")

app = FastAPI(title="KrishiMitra Twilio Voice Webhooks")

_TWIML_TYPE = "text/xml; charset=utf-8"


def _twiml_response(vr: VoiceResponse) -> Response:
    body = str(vr)
    return Response(content=body.encode("utf-8"), media_type=_TWIML_TYPE)


def _say_safe(vr: VoiceResponse, text: str, *, language: str) -> None:
    t = escape((text or "").strip() or " ")
    lang = (language or "en-US")[:12]
    vr.say(t, language=lang)


def _public_base() -> str:
    return voice_public_base_url()


def _error_twiml(message: str) -> Response:
    vr = VoiceResponse()
    _say_safe(vr, message, language="en-US")
    vr.hangup()
    return _twiml_response(vr)


@app.exception_handler(Exception)
async def _any_exception_handler(request: StarletteRequest, exc: Exception) -> Response:
    log.error("Unhandled %s %s: %s", request.method, request.url.path, exc)
    traceback.print_exc()
    return _error_twiml("A server error occurred. Goodbye.")


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: StarletteRequest, exc: RequestValidationError) -> Response:
    log.warning("Validation %s %s: %s", request.method, request.url.path, exc.errors())
    return _error_twiml("Invalid voice webhook request. Goodbye.")


@app.middleware("http")
async def _log_requests(request: Request, call_next):
    log.info("%s %s", request.method, request.url.path)
    return await call_next(request)


@app.api_route("/voice/twilio-ping", methods=["GET", "POST"])
def twilio_ping():
    """Minimal TwiML — verify Twilio can reach this app (set call URL to .../voice/twilio-ping)."""
    vr = VoiceResponse()
    _say_safe(vr, "KrishiMitra voice webhook is working.", language="en-US")
    vr.hangup()
    return _twiml_response(vr)


@app.api_route("/voice/start/{session_id}", methods=["GET", "POST"])
def voice_start(session_id: str):
    ctx = session_store.get_session(session_id)
    if not ctx:
        return _error_twiml(
            "Sorry, this call session is not available. Run the call script again, then answer."
        )

    lang = (ctx.get("speech_language") or "en-IN")[:12]
    intro = ctx.get("intro_script") or (
        f"Hello {ctx.get('farmer_name', 'farmer')}. This is KrishiMitra advisory. "
        f"{ctx.get('why_now', '')} "
        "If you have a question, please speak after the tone."
    )
    if len(intro) > 1200:
        intro = intro[:1197] + "..."

    base = _public_base()
    if not base:
        return _error_twiml(
            "Voice webhook is misconfigured. Set public voice base URL in environment on the server."
        )

    action = f"{base.rstrip('/')}/voice/gather/{session_id}"

    vr = VoiceResponse()
    _say_safe(vr, intro, language=lang)

    gather = Gather(
        input="speech",
        action=action,
        method="POST",
        speech_timeout="auto",
        language=lang,
    )
    _say_safe(gather, "Please ask your question now.", language=lang)
    vr.append(gather)
    _say_safe(vr, "We did not hear anything. Goodbye.", language=lang)
    vr.hangup()
    return _twiml_response(vr)


@app.post("/voice/gather/{session_id}")
def voice_gather(
    session_id: str,
    SpeechResult: Optional[str] = Form(None),
    Confidence: Optional[str] = Form(None),
):
    ctx = session_store.get_session(session_id) or {}
    user_speech = SpeechResult or ""
    text = reply_mod.personalized_reply(ctx, user_speech)

    vr = VoiceResponse()
    _say_safe(vr, text, language=(ctx.get("speech_language") or "en-US")[:12])
    vr.hangup()
    return _twiml_response(vr)


@app.get("/health")
def health():
    return {"status": "ok", "module": "twilio_voice_webhook"}
