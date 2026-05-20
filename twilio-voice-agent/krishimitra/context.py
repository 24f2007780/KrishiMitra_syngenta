"""Build Gemini system instructions from KrishiMitra farmer context."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

_BASE = Path(__file__).resolve().parents[1]
_PERSONA_PATH = _BASE / "config" / "persona.txt"


def load_base_persona() -> str:
    try:
        return _PERSONA_PATH.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return (
            "You are KrishiMitra, a trusted agricultural advisory voice assistant for Indian farmers. "
            "Speak simply, in the farmer's language, with no marketing hype."
        )


def build_system_instruction(ctx: Optional[Dict[str, Any]]) -> str:
    base = load_base_persona()
    if not ctx:
        return base

    name = ctx.get("farmer_name") or ctx.get("name") or "farmer"
    crop = ctx.get("crop") or (ctx.get("crops") or ["crop"])[0] if isinstance(ctx.get("crops"), list) else "crop"
    district = ctx.get("district", "")
    state = ctx.get("state", "")
    stage = ctx.get("crop_stage") or ctx.get("confirmed_stage", "")
    pest = ctx.get("pest_risk_level") or ctx.get("active_pest", "")
    why = ctx.get("why_now") or ctx.get("why_now_reason_local") or ctx.get("why_now_reason_en", "")
    product = ctx.get("recommended_product") or ctx.get("top_product", "")
    retailer = ctx.get("retailer_name") or ctx.get("linked_retailer_name", "")
    lang = ctx.get("preferred_language") or ctx.get("language", "English")
    urgency = ctx.get("urgency_score")

    block = f"""
# This call — farmer context (use in every reply)
- Farmer name: {name}
- Location: {district}, {state}
- Crop: {crop}
- Growth stage: {stage}
- Pest / risk: {pest}
- Why outreach now: {why}
- Suggested product (if relevant): {product}
- Local agro retailer: {retailer}
- Preferred language: {lang}
- Urgency score (0-1): {urgency if urgency is not None else "not set"}

Greet the farmer by name. Explain the situation in simple words. Answer their questions about crop care and when to visit the retailer. Do not invent prices or government schemes you were not given.

On this call, your FIRST spoken reply should sound like a real field advisory (not "this is KrishiMitra"). Use the intro example style from context if provided.
"""
    return base + "\n" + block.strip()


def build_phone_intro(ctx: Optional[Dict[str, Any]]) -> tuple[str, str]:
    """
    Short spoken intro for Twilio <Say> before Gemini connects.
    Returns (text, bcp47_language) e.g. hi-IN for Hindi/Bhojpuri region.
    """
    if not ctx:
        return (
            "Namaskar. KrishiMitra se ek chhoti kheti salah. Kripya line par rahen.",
            "hi-IN",
        )

    if ctx.get("intro_script"):
        lang = _say_language(ctx.get("preferred_language") or "")
        return str(ctx["intro_script"]).strip(), lang

    name = ctx.get("farmer_name") or "kisan bhai"
    village = ctx.get("village") or ctx.get("district") or ""
    district = ctx.get("district", "")
    crop = ctx.get("crop") or (ctx.get("crops") or ["fasal"])[0]
    stage = ctx.get("crop_stage") or ""
    pest = ctx.get("active_pest") or ctx.get("pest_risk_level") or ""
    product = ctx.get("recommended_product") or ""
    retailer = ctx.get("retailer_name") or "apke nazdeeki krishi dukan"

    # Hindi / Bhojpuri region — natural phone advisory (Devanagari for Polly hi-IN)
    place = village or district
    intro_hi = (
        f"प्रणाम {name} जी। मैं आपके खेत की जानकारी के साथ कृषि मित्र से बोल रहा हूँ। "
        f"{'आपके ' + place + ' में ' if place else ''}"
        f"आपका {crop} अभी {stage} अवस्था में है। "
        f"पिछले कुछ दिनों से नमी ज्यादा रही है, इससे {pest} का खतरा बढ़ा है। "
        f"समय रहते {product} का छिड़काव और {retailer} से सलाह लेना फायदेमंद हो सकता है। "
        f"अगर कोई सवाल हो तो अभी पूछिए, मैं सुन रहा हूँ।"
    )
    return intro_hi, _say_language(ctx.get("preferred_language") or "")


def _say_language(preferred: str) -> str:
    p = (preferred or "").lower()
    if p in (
        "bhojpuri",
        "hindi",
        "marathi",
        "tamil",
        "telugu",
        "kannada",
        "bengali",
        "gujarati",
        "gujrati",
    ):
        if p == "tamil":
            return "ta-IN"
        if p == "telugu":
            return "te-IN"
        if p == "marathi":
            return "mr-IN"
        if p == "kannada":
            return "kn-IN"
        if p == "bengali":
            return "bn-IN"
        if p in ("gujarati", "gujrati"):
            return "gu-IN"
        return "hi-IN"
    return "en-IN"


def escape_twiml_say(text: str) -> str:
    from xml.sax.saxutils import escape

    return escape(text)
