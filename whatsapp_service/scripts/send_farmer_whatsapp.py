#!/usr/bin/env python3
"""CLI: send KrishiMitra WhatsApp from a farmer context JSON (voice-agent format)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO = Path(__file__).resolve().parents[2]
load_dotenv(_REPO / ".env")

if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from sms_service.context import build_whatsapp_body, load_farmer_context  # noqa: E402
from whatsapp_service.send import send_farmer_whatsapp  # noqa: E402

DEFAULT_JSON = _REPO / "twilio-voice-agent" / "config" / "farmer_mayur.example.json"


def _resolve_json_path(raw: str) -> Path:
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Send KrishiMitra WhatsApp from farmer context JSON",
    )
    parser.add_argument(
        "--json",
        dest="json_path",
        default=str(DEFAULT_JSON),
        help="Farmer context JSON (same as voice calls)",
    )
    parser.add_argument("--to", help="Override to_number (E.164)")
    parser.add_argument("--body", help="Override message text")
    parser.add_argument("--dry-run", action="store_true", help="Do not connect or send")
    parser.add_argument("--preview", action="store_true", help="Print body only")
    parser.add_argument(
        "--host",
        default=os.getenv("M11_HOST", "127.0.0.1"),
        help="M11 host when using --api",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("M11_PORT", "8011")),
        help="M11 port when using --api",
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="POST to whatsapp_service /whatsapp/send",
    )
    parser.add_argument(
        "--connect-timeout",
        type=float,
        default=180,
        help="Seconds to wait for WhatsApp Web session",
    )
    args = parser.parse_args()

    path = _resolve_json_path(args.json_path)
    ctx = load_farmer_context(path)

    if args.to:
        ctx["to_number"] = args.to

    body = args.body or build_whatsapp_body(ctx)
    to = ctx.get("to_number", "")

    if args.preview:
        print(f"To:   {to}")
        print(f"Body ({len(body)} chars):\n{body}")
        return

    if args.api:
        import httpx

        url = f"http://{args.host}:{args.port}/whatsapp/send"
        payload = {**ctx, "dry_run": args.dry_run, "connect_timeout": args.connect_timeout}
        if args.body:
            payload["whatsapp_script"] = args.body
        print(f"POST {url}")
        r = httpx.post(url, json=payload, timeout=max(args.connect_timeout + 30, 60))
        print(r.status_code, r.text)
        if r.status_code >= 400:
            sys.exit(1)
        return

    try:
        out = send_farmer_whatsapp(
            ctx,
            body=args.body,
            dry_run=args.dry_run,
            connect_timeout=args.connect_timeout,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
