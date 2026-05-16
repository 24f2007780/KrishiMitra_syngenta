"""
FastAPI app Twilio calls for voice: opening TwiML + speech Gather + LLM reply.

Twilio must reach this server on the public internet (ngrok in dev).
Set PUBLIC_VOICE_BASE_URL before placing a call (the CLI sets it from ngrok).
"""

from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import Response
from twilio.twiml.voice_response import Gather, VoiceResponse

from twilio_apps.call import reply as reply_mod
from twilio_apps.call import session_store

app = FastAPI(title="KrishiMitra Twilio Voice Webhooks")


def _public_base() -> str:
    return (os.environ.get("PUBLIC_VOICE_BASE_URL") or "").rstrip("/")


@app.get("/voice/start")
def voice_start(session_id: str = Query(..., description="Server-side session key")):
    ctx = session_store.get_session(session_id)
    if not ctx:
        vr = VoiceResponse()
        vr.say("Sorry, this call session is not available. Goodbye.")
        vr.hangup()
        return Response(content=str(vr), media_type="application/xml")

    lang = ctx.get("speech_language") or "en-IN"
    name = ctx.get("farmer_name", "farmer")
    intro = ctx.get("intro_script") or (
        f"Hello {name}. This is an automated advisory call from KrishiMitra. "
        f"{ctx.get('why_now', '')} "
        "If you have a question, please speak after the tone."
    )
    # Twilio Say length limits — keep intro reasonable
    if len(intro) > 1200:
        intro = intro[:1197] + "..."

    base = _public_base()
    action = f"{base}/voice/gather?session_id={session_id}" if base else ""

    vr = VoiceResponse()
    vr.say(intro, language=lang)

    if action:
        gather = Gather(
            input="speech",
            action=action,
            method="POST",
            speech_timeout="auto",
            language=lang,
        )
        gather.say("Please ask your question now.", language=lang)
        vr.append(gather)
        vr.say("We did not hear anything. Goodbye.", language=lang)
    else:
        vr.say("Voice gather is not configured. Goodbye.", language="en-IN")

    vr.hangup()
    return Response(content=str(vr), media_type="application/xml")


@app.post("/voice/gather")
def voice_gather(
    request: Request,
    session_id: str = Query(...),
    SpeechResult: Optional[str] = Form(None),
    Confidence: Optional[str] = Form(None),
):
    ctx = session_store.get_session(session_id) or {}
    user_speech = SpeechResult or ""
    text = reply_mod.personalized_reply(ctx, user_speech)

    vr = VoiceResponse()
    vr.say(text, language=ctx.get("speech_language") or "en-IN")
    vr.hangup()
    return Response(content=str(vr), media_type="application/xml")


@app.get("/health")
def health():
    return {"status": "ok", "module": "twilio_voice_webhook"}
