#!/usr/bin/env python3
"""CLI: place a KrishiMitra outbound voice call via POST /krishimitra/call."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".." / ".env")
load_dotenv(ROOT / ".env")

DEFAULT_EXAMPLE = ROOT / "config" / "farmer_context.example.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="KrishiMitra outbound voice call")
    parser.add_argument("--to", help="E.164 phone number")
    parser.add_argument("--host", default=os.getenv("VOICE_AGENT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")))
    parser.add_argument("--json", dest="json_path", help="Farmer context JSON file")
    args = parser.parse_args()

    path = Path(args.json_path) if args.json_path else DEFAULT_EXAMPLE
    if not path.is_file():
        print(f"Missing JSON: {path}", file=sys.stderr)
        sys.exit(1)

    body = json.loads(path.read_text(encoding="utf-8"))
    if args.to:
        body["to_number"] = args.to

    url = f"http://{args.host}:{args.port}/krishimitra/call"
    print(f"POST {url}")
    r = httpx.post(url, json=body, timeout=60.0)
    print(r.status_code, r.text)
    if r.status_code >= 400:
        sys.exit(1)


if __name__ == "__main__":
    main()
