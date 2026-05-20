#!/usr/bin/env python3
"""
Interactive or CLI Twilio SMS test.

Run from repo root (KrishiMitra_syngenta):

    python -m twilio_apps.sms.app
    python -m twilio_apps.sms.app --to +15551234567 --body "Hello" --dry-run
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (parent of twilio_apps/)
_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_ROOT / ".env")

from twilio_apps.sms.client import send_sms  # noqa: E402


def _prompt(msg: str, default: str | None = None) -> str:
    hint = f" [{default}]" if default else ""
    s = input(f"{msg}{hint}: ").strip()
    if not s and default is not None:
        return default
    return s


def main() -> None:
    parser = argparse.ArgumentParser(description="Send a test SMS via Twilio")
    parser.add_argument("--to", help="Destination E.164, e.g. +919876543210")
    parser.add_argument("--body", help="Message text")
    parser.add_argument(
        "--json",
        dest="json_path",
        help="Farmer context JSON (uses sms_service; same as voice agent)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not call Twilio")
    parser.add_argument("--preview", action="store_true", help="With --json: print SMS only")
    args = parser.parse_args()

    if args.json_path:
        if str(_ROOT) not in sys.path:
            sys.path.insert(0, str(_ROOT))
        from sms_service.context import build_sms_body, load_farmer_context
        from sms_service.send import send_farmer_sms

        ctx = load_farmer_context(Path(args.json_path))
        if args.to:
            ctx["to_number"] = args.to
        if args.preview:
            print(build_sms_body(ctx))
            return
        try:
            out = send_farmer_sms(ctx, body=args.body, dry_run=args.dry_run)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(out)
        return

    if args.to and args.body is not None:
        to = args.to
        body = args.body
        dry = args.dry_run
    else:
        print("Twilio SMS test (Ctrl+C to cancel)\n")
        default_to = os.environ.get("TEST_PHONE_NUMBER", "")
        to = _prompt("To number (E.164)", default_to or None)
        if not to:
            print("Need a destination number.", file=sys.stderr)
            sys.exit(1)
        body = _prompt("Message body", "KrishiMitra test SMS.")
        dry_s = _prompt("Dry run? (y/n)", "n").lower()
        dry = dry_s.startswith("y")

    try:
        out = send_sms(to, body, dry_run=dry)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(out)


if __name__ == "__main__":
    main()
