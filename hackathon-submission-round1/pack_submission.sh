#!/usr/bin/env bash
# Pack Round 1 submission zip. Edit TEAM_NAME before running.
set -euo pipefail

# ============ EDIT THIS ============
TEAM_NAME="YOUR_REGISTERED_TEAM_NAME"
# ===================================

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGE="/tmp/${TEAM_NAME}"
GUIDE="${ROOT}/hackathon-submission-round1"

if [[ "$TEAM_NAME" == "YOUR_REGISTERED_TEAM_NAME" ]]; then
  echo "Edit TEAM_NAME in pack_submission.sh first."
  exit 1
fi

rm -rf "$STAGE"
mkdir -p "$STAGE"

cp "$GUIDE/01_README_FOR_SUBMISSION.md" "$STAGE/README.md"
cp "$GUIDE/02_TEAM_MEMBERS.md"         "$STAGE/TEAM_MEMBERS.md"
cp "$GUIDE/04_SETUP_AND_RUN.md"         "$STAGE/SETUP_AND_RUN.md"
cp "$GUIDE/07_API_AND_ENVIRONMENT.md" "$STAGE/API_AND_ENVIRONMENT.md"
cp "$GUIDE/09_DEMO_RUNBOOK_FOR_JUDGES.md" "$STAGE/DEMO_RUNBOOK.md"

if [[ -f "$GUIDE/SOLUTION.pdf" ]]; then
  cp "$GUIDE/SOLUTION.pdf" "$STAGE/"
else
  echo "Note: Add SOLUTION.pdf to hackathon-submission-round1/ before packing (export from slides)."
fi

if [[ -f "$GUIDE/DEMO_VIDEO_LINK.txt" ]]; then
  cp "$GUIDE/DEMO_VIDEO_LINK.txt" "$STAGE/"
else
  echo "https://[FILL_IN_VIDEO_URL]" > "$STAGE/DEMO_VIDEO_LINK.txt"
fi

cp "$ROOT/twilio-voice-agent/config/farmer_mayur.example.json" "$STAGE/demo_farmer_mayur.json" 2>/dev/null || true

cd /tmp
zip -r "${TEAM_NAME}.zip" "$TEAM_NAME"
echo "Created: /tmp/${TEAM_NAME}.zip"
ls -lh "/tmp/${TEAM_NAME}.zip"
