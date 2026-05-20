#!/usr/bin/env bash
# KrishiMitra voice agent — ngrok (optional) + FastAPI + uvicorn (run from repo root: ./start.sh)
# Requires: pip install -r requirements.txt (use a venv below or set PYTHON_CMD)
#
# Default: starts ngrok for PORT, sets TUNNEL_LINK to the public https URL, then runs the app.
# Skip tunnel: START_NGROK=0 ./start.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# Default venv (override with PYTHON_CMD=/path/to/python)
DEFAULT_VENV_PYTHON="/storage/.venvs/vedantu-voice-agent/bin/python"

if [[ -z "${PYTHON_CMD:-}" ]]; then
  if [[ -x "$DEFAULT_VENV_PYTHON" ]]; then
    PYTHON_CMD="$DEFAULT_VENV_PYTHON"
  elif [[ -x "$ROOT/venv/bin/python" ]]; then
    PYTHON_CMD="$ROOT/venv/bin/python"
  elif [[ -n "${VIRTUAL_ENV:-}" && -x "${VIRTUAL_ENV}/bin/python" ]]; then
    PYTHON_CMD="${VIRTUAL_ENV}/bin/python"
  else
    PYTHON_CMD="python3"
  fi
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
# Default: run ngrok. Set START_NGROK=0 to use only TUNNEL_LINK from .env.
START_NGROK="${START_NGROK:-1}"

fetch_ngrok_public_url() {
  curl -fsS http://127.0.0.1:4040/api/tunnels 2>/dev/null \
    | python3 -c '
import json, sys
d = json.load(sys.stdin)
ts = d.get("tunnels") or []
u = next((t.get("public_url", "") for t in ts if t.get("proto") == "https"), "")
if not u and ts:
    u = ts[0].get("public_url", "") or ""
print(u)
' 2>/dev/null || true
}

start_ngrok_and_export_tunnel() {
  if [[ "$START_NGROK" != "1" ]]; then
    echo "ngrok: skipped (START_NGROK=$START_NGROK). Using TUNNEL_LINK from env/.env if set."
    return 0
  fi
  if ! command -v ngrok >/dev/null 2>&1; then
    echo "ngrok: not on PATH — start the app without a tunnel or install ngrok."
    return 0
  fi
  if ! command -v curl >/dev/null 2>&1; then
    echo "curl: not on PATH — cannot read ngrok API; skipping TUNNEL_LINK."
    return 0
  fi

  mkdir -p "$ROOT/logs"
  local log_file="$ROOT/logs/ngrok.log"

  # If you use a reserved domain: NGROK_DOMAIN=your-name.ngrok-free.app ./start.sh
  if [[ -n "${NGROK_DOMAIN:-}" ]]; then
    ngrok http "$PORT" --domain="$NGROK_DOMAIN" --log=stdout >"$log_file" 2>&1 &
  else
    ngrok http "$PORT" --log=stdout >"$log_file" 2>&1 &
  fi

  local public=""
  local _i
  for ((_i = 0; _i < 40; _i++)); do
    public="$(fetch_ngrok_public_url)"
    if [[ -n "$public" ]]; then
      export TUNNEL_LINK="$public"
      echo "ngrok:  $public"
      echo "export TUNNEL_LINK=$public"
      return 0
    fi
    sleep 0.25
  done

  echo "ngrok: tunnel URL not detected (see $log_file)."
  return 0
}

echo "Python: $PYTHON_CMD"
echo "Local:  http://${HOST}:${PORT}/"
echo "        http://${HOST}:${PORT}/login  → dashboard"
echo ""

start_ngrok_and_export_tunnel

exec "$PYTHON_CMD" -m uvicorn app:app --host "$HOST" --port "$PORT" --reload
