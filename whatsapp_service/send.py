"""Send WhatsApp using farmer context JSON (same shape as voice / SMS)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from sms_service.context import build_whatsapp_body, resolve_to_number


def send_farmer_whatsapp(
    ctx: Dict[str, Any],
    *,
    to: Optional[str] = None,
    body: Optional[str] = None,
    dry_run: bool = False,
    connect_timeout: float = 180,
    max_length: int = 4096,
) -> Dict[str, Any]:
    """
    Send (or dry-run) a WhatsApp advisory for one farmer context dict.

    Requires a linked session: ``python -m whatsapp_apps.web.app login`` once.
    """
    from whatsapp_apps.web.client import send_whatsapp

    to_e164 = resolve_to_number(ctx, to)
    message = body if body is not None else build_whatsapp_body(ctx, max_length=max_length)

    result = send_whatsapp(
        to_e164,
        message,
        dry_run=dry_run,
        connect_timeout=connect_timeout,
    )
    result["farmer_name"] = ctx.get("farmer_name")
    result["farmer_id"] = ctx.get("farmer_id")
    result["context_source"] = "farmer_json"
    return result
