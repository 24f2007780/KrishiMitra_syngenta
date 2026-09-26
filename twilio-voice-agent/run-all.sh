#!/usr/bin/env bash
# KrishiMitra voice agent — reference command list.
#
# This file is NOT meant to be executed top-to-bottom (source it, or copy
# individual lines). Running it directly just prints usage and exits, so a
# real outbound call is never placed by accident.
#
# Usage: ./run-all.sh <command>
#   ./run-all.sh start          # start ngrok + FastAPI (foreground)
#   ./run-all.sh health         # GET /krishimitra/health
#   ./run-all.sh preview        # POST /krishimitra/preview-instruction (safe, no call)
#   ./run-all.sh call           # POST /krishimitra/call  <-- places a REAL Twilio call
#   ./run-all.sh call-script    # same call, via scripts/krishimitra_call.py

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
BASE="http://${HOST}:${PORT}"

cmd="${1:-}"

case "$cmd" in
  start)
    # Starts ngrok tunnel + FastAPI/uvicorn (foreground; Ctrl+C to stop).
    ./start.sh
    ;;

  health)
    curl -s "${BASE}/krishimitra/health" | python3 -m json.tool
    ;;

  preview)
    # Safe: builds the system instruction / phone intro from farmer JSON, places no call.
    curl -s -X POST "${BASE}/krishimitra/preview-instruction" \
      -H "Content-Type: application/json" \
      -d @config/farmer_context.example.json | python3 -m json.tool
    ;;

  call)
    # REAL CALL: this dials config/farmer_context.example.json's to_number via Twilio.
    # Edit that file (or pass your own JSON) before running.
    curl -s -X POST "${BASE}/krishimitra/call" \
      -H "Content-Type: application/json" \
      -d @config/farmer_context.example.json | python3 -m json.tool
    ;;

  call-script)
    # REAL CALL: equivalent to `call`, via the CLI wrapper.
    # Override the destination number: --to +91XXXXXXXXXX
    # Use a different farmer profile: --json config/farmer_mayur.example.json
    "$ROOT/../.venv/bin/python" scripts/krishimitra_call.py --json config/farmer_context.example.json
    ;;

  *)
    echo "Usage: $0 {start|health|preview|call|call-script}"
    echo ""
    echo "  start        start ngrok + FastAPI (foreground)"
    echo "  health       GET  /krishimitra/health          (safe)"
    echo "  preview      POST /krishimitra/preview-instruction (safe, no call)"
    echo "  call         POST /krishimitra/call             (REAL Twilio call)"
    echo "  call-script  scripts/krishimitra_call.py          (REAL Twilio call)"
    exit 1
    ;;
esac
