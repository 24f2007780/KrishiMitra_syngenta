"""Build SMS body text from the same farmer JSON used for voice calls."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

# Default max ~2 GSM segments; Unicode (Gujarati etc.) may bill as more segments.
DEFAULT_MAX_LENGTH = 320
WHATSAPP_DEFAULT_MAX_LENGTH = 4096


def normalize_e164(phone: str) -> str:
    """Strip spaces/dashes; ensure leading + for E.164."""
    s = re.sub(r"[\s\-()]", "", (phone or "").strip())
    if not s:
        raise ValueError("Missing phone number")
    if not s.startswith("+"):
        if s.startswith("91") and len(s) >= 12:
            s = "+" + s
        elif len(s) == 10 and s.isdigit():
            s = "+91" + s
        else:
            s = "+" + s
    return s


def load_farmer_context(path: Path | str) -> Dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Farmer context file not found: {p}")
    return json.loads(p.read_text(encoding="utf-8"))


def build_sms_body(ctx: Dict[str, Any], *, max_length: int = DEFAULT_MAX_LENGTH) -> str:
    """
    Build outbound SMS text from farmer context.

    Priority: sms_script / sms_body → example_message_en → intro_script (trimmed)
    → auto-generated English advisory.
    """
    return build_advisory_body(
        ctx,
        channel="sms",
        max_length=max_length,
    )


def build_whatsapp_body(
    ctx: Dict[str, Any], *, max_length: int = WHATSAPP_DEFAULT_MAX_LENGTH
) -> str:
    """
    Build WhatsApp message from farmer context.

    Priority: whatsapp_script → sms_script → example_message_en → intro_script
    → auto-generated English advisory.
    """
    return build_advisory_body(
        ctx,
        channel="whatsapp",
        max_length=max_length,
    )


def build_advisory_body(
    ctx: Dict[str, Any],
    *,
    channel: str = "sms",
    max_length: int = DEFAULT_MAX_LENGTH,
) -> str:
    if channel == "whatsapp":
        keys = (
            "whatsapp_script",
            "whatsapp_body",
            "sms_script",
            "sms_body",
            "example_message_en",
        )
    else:
        keys = ("sms_script", "sms_body", "example_message_en")

    for key in keys:
        raw = ctx.get(key)
        if raw and str(raw).strip():
            return _truncate(str(raw).strip(), max_length)

    intro = ctx.get("intro_script")
    if intro and str(intro).strip():
        return _truncate(str(intro).strip(), max_length)

    return _truncate(_auto_body_en(ctx), max_length)


def _auto_body_en(ctx: Dict[str, Any]) -> str:
    name = ctx.get("farmer_name") or "farmer"
    village = ctx.get("village") or ""
    district = ctx.get("district") or ""
    state = ctx.get("state") or ""
    place = ", ".join(x for x in (village, district, state) if x)
    crop = ctx.get("crop") or _first_crop(ctx)
    stage = ctx.get("crop_stage") or ""
    pest = ctx.get("active_pest") or ctx.get("pest_risk_level") or ""
    product = ctx.get("recommended_product") or ""
    retailer = ctx.get("retailer_name") or "your local agro store"
    why = ctx.get("why_now") or ""

    lines = [f"KrishiMitra — Hello {name} ji."]
    if place and crop:
        lines.append(f"Your {crop}" + (f" ({stage})" if stage else "") + f" in {place}.")
    elif crop:
        lines.append(f"Your {crop}" + (f" is in {stage} stage." if stage else "") + ".")
    if pest:
        lines.append(f"Alert: {pest} risk.")
    if why:
        lines.append(why)
    if product:
        lines.append(f"Consider {product} in time; ask at {retailer}.")
    lines.append("Reply or call your advisor for questions.")
    return " ".join(lines)


def _first_crop(ctx: Dict[str, Any]) -> str:
    crops = ctx.get("crops")
    if isinstance(crops, list) and crops:
        return str(crops[0])
    return "crop"


def _truncate(text: str, max_length: int) -> str:
    if max_length <= 0 or len(text) <= max_length:
        return text
    if max_length <= 3:
        return text[:max_length]
    return text[: max_length - 3].rstrip() + "..."


def resolve_to_number(ctx: Dict[str, Any], override: Optional[str] = None) -> str:
    raw = override or ctx.get("to_number") or ctx.get("phone") or ""
    return normalize_e164(str(raw))
