"""Generate a short spoken reply from farmer context + what the user said (STT text)."""

from __future__ import annotations

import os
from typing import Any, Dict


def personalized_reply(context: Dict[str, Any], user_speech: str) -> str:
    """
    Return plain text suitable for Twilio <Say> (keep it short; avoid special XML chars).
    """
    speech = (user_speech or "").strip()
    if not speech:
        return "I did not catch that. Please call again or visit your agro dealer. Goodbye."

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # No LLM: still acknowledge with context hints
        name = context.get("farmer_name", "farmer")
        retailer = context.get("retailer_name", "your dealer")
        return (
            f"Thank you {name}. For details about your crop, please speak with {retailer}. Goodbye."
        )

    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        ctx_lines = "\n".join(f"{k}: {v}" for k, v in context.items() if v is not None)
        user = (
            f"Farmer context:\n{ctx_lines}\n\n"
            f"Farmer said (speech-to-text): {speech}\n\n"
            "Reply as a trusted agronomy advisor in at most 3 short sentences. "
            "Use simple words. No lists, no markdown, no exclamation marks. "
            "If the farmer's preferred language is not English, reply in that language."
        )
        msg = client.messages.create(
            model=model,
            max_tokens=220,
            messages=[{"role": "user", "content": user}],
        )
        text = ""
        for block in msg.content:
            if hasattr(block, "text"):
                text += block.text
        text = (text or "").strip().replace("&", "and").replace("<", "").replace(">", "")
        if len(text) > 450:
            text = text[:447] + "..."
        return text or "Thank you. Goodbye."
    except Exception:
        return "Sorry, I could not answer right now. Please contact your agro dealer. Goodbye."
