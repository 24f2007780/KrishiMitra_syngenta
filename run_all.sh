#!/bin/bash
# Syngenta KrishiMitra — start core microservices.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

export PYTHONPATH="${PYTHONPATH:-}:."

PYTHON="${ROOT}/.venv/bin/python3"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

echo "🚀 Starting Syngenta KrishiMitra Microservices..."

echo "📦 Bootstrapping database (farmers + products if empty)..."
"$PYTHON" scripts/bootstrap_db.py

echo "Starting services..."
# Tier 1 — Farmer DB (M1)
"$PYTHON" -m uvicorn farmer_service.main:app --host 0.0.0.0 --port 8001 &

# Tier 2 — Signals + context (M4, M5, M6)
"$PYTHON" -m uvicorn weather_service.main:app --host 0.0.0.0 --port 8004 &
"$PYTHON" -m uvicorn calendar_service.main:app --host 0.0.0.0 --port 8005 &
"$PYTHON" -m uvicorn context_service.main:app --host 0.0.0.0 --port 8006 &

# Tier 3 — Intelligence (M7 urgency, campaign receptivity, M8 product ranker)
"$PYTHON" -m uvicorn urgency_scorer.main:app --host 0.0.0.0 --port 8007 &
"$PYTHON" -m uvicorn campaign_receptivity_engine.main:app --host 0.0.0.0 --port 8009 &
"$PYTHON" -m uvicorn product_service.main:app --host 0.0.0.0 --port 8008 &

# Tier 4+ (uncomment when implemented)
# "$PYTHON" -m uvicorn sms_service.main:app --host 0.0.0.0 --port 8010 &
# "$PYTHON" -m uvicorn whatsapp_service.main:app --host 0.0.0.0 --port 8011 &

echo "✅ Active: M1 (8001), M4–M6 (8004–8006), M7 (8007), M8 (8008), receptivity (8009)."
echo "   Health: curl http://127.0.0.1:8001/health … http://127.0.0.1:8008/health"
echo "   Stop all: ./stop_all.sh"
