"""Send SMS using farmer context JSON (same shape as twilio-voice-agent)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from sms_service.context import build_sms_body, resolve_to_number


def send_farmer_sms(
    ctx: Dict[str, Any],
    *,
    to: Optional[str] = None,
    body: Optional[str] = None,
    dry_run: bool = False,
    max_length: int = 320,
) -> Dict[str, Any]:
    """
    Send (or dry-run) an advisory SMS for one farmer context dict.

    Returns Twilio client result plus ``farmer_name`` and generated ``body``.
    """
    from twilio_apps.sms.client import send_sms

    to_e164 = resolve_to_number(ctx, to)
    message = body if body is not None else build_sms_body(ctx, max_length=max_length)

    result = send_sms(to_e164, message, dry_run=dry_run)
    result["farmer_name"] = ctx.get("farmer_name")
    result["farmer_id"] = ctx.get("farmer_id")
    result["context_source"] = "farmer_json"
    return result
