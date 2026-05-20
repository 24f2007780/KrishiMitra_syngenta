#!/usr/bin/env python3
"""CLI: send KrishiMitra SMS from a farmer context JSON (voice-agent format)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO = Path(__file__).resolve().parents[2]
load_dotenv(_REPO / ".env")

# Run from repo root: python -m sms_service.scripts.send_farmer_sms
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from sms_service.context import build_sms_body, load_farmer_context  # noqa: E402
from sms_service.send import send_farmer_sms  # noqa: E402

DEFAULT_JSON = _REPO / "twilio-voice-agent" / "config" / "farmer_mayur.example.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send KrishiMitra SMS from farmer context JSON",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        default=str(DEFAULT_JSON),
        help="Farmer context JSON (same as voice calls)",
    )
    parser.add_argument("--to", help="Override to_number (E.164)")
    parser.add_argument("--body", help="Override SMS text (skip auto-build)")
    parser.add_argument("--dry-run", action="store_true", help="Do not call Twilio")
    parser.add_argument("--preview", action="store_true", help="Print body only, do not send")
    parser.add_argument(
        "--host",
        default=os.getenv("M10_HOST", "127.0.0.1"),
        help="Use HTTP API instead of direct send (with --api)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("M10_PORT", "8010")),
        help="M10 port when using --api",
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="POST to sms_service /sms/send instead of direct Twilio",
    )
    args = parser.parse_args()

    path = _resolve_json_path(args.json_path)
    ctx = load_farmer_context(path)

    if args.to:
        ctx["to_number"] = args.to

    body = args.body or build_sms_body(ctx)
    to = ctx.get("to_number", "")

    if args.preview:
        print(f"To:   {to}")
        print(f"Body ({len(body)} chars):\n{body}")
        return

    if args.api:
        import httpx

        url = f"http://{args.host}:{args.port}/sms/send"
        payload = {**ctx, "dry_run": args.dry_run}
        if args.body:
            payload["sms_script"] = args.body
        print(f"POST {url}")
        r = httpx.post(url, json=payload, timeout=60.0)
        print(r.status_code, r.text)
        if r.status_code >= 400:
            sys.exit(1)
        return

    try:
        out = send_farmer_sms(ctx, body=args.body, dry_run=args.dry_run)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(out, indent=2, ensure_ascii=False))


def _resolve_json_path(raw: str) -> Path:
    """Accept paths relative to cwd or twilio-voice-agent/config/."""
    p = Path(raw)
    if p.is_file():
        return p
    voice_cfg = _REPO / "twilio-voice-agent" / "config" / p.name
    if voice_cfg.is_file():
        return voice_cfg
    cwd_cfg = Path.cwd() / "config" / p.name
    if cwd_cfg.is_file():
        return cwd_cfg
    return p


if __name__ == "__main__":
    main()
