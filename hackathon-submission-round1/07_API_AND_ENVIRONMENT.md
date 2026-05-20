# API and environment requirements

For judges and organizers — what external services KrishiMitra uses and what must be configured locally.

---

## Runtime environment

| Item | Requirement |
|------|-------------|
| OS | Linux, macOS, or WSL2 |
| Python | 3.11+ (project tested on 3.14 in venv) |
| RAM | ≥ 4 GB recommended |
| Network | Required for weather API, Twilio, Gemini, ngrok (voice) |
| Disk | ~500 MB with venv (exclude venv from zip) |

---

## Core microservices (no paid API keys)

| Service | Port | External dependency |
|---------|------|---------------------|
| M1 Farmer DB | 8001 | SQLite local `master.db` |
| M4 Weather | 8004 | Open-Meteo (free), Nominatim geocoding |
| M5 Calendar | 8005 | Local JSON / ICAR-style rules |
| M6 Context | 8006 | Calls M1, M4, M5 over localhost |
| M8 Product ranker | 8008 | SQLite products + `canonical_products.json` |
| M7 Urgency (optional) | 8007 | Local ML pickles in `urgency_scorer/ml/` |

**Start:** `./run_all.sh` after `python scripts/bootstrap_db.py`

---

## Optional — outbound channels

### Twilio (SMS + voice)

| Variable | Purpose |
|----------|---------|
| `TWILIO_ACCOUNT_SID` | Account |
| `TWILIO_AUTH_TOKEN` | Auth |
| `TWILIO_PHONE_NUMBER` | From number (E.164) |

**Trial accounts:** destination numbers must be verified in Twilio console.

**Voice additionally:**

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Google Gemini Live (voice AI) |
| `TUNNEL_LINK` / `NGROK_PUBLIC_URL` | Public HTTPS for Twilio webhooks |
| ngrok | `ngrok http 8000` (see `twilio-voice-agent/start.sh`) |

### WhatsApp Web (demo — not Meta Cloud API)

| Package | `neonize`, `protobuf>=7.34.1`, `qrcode` |
| Session | `whatsapp_apps/web/sessions/*.sqlite3` (QR login once) |
| Env | `TEST_WHATSAPP_NUMBER` optional |

### Anthropic Claude (planned M9–M12)

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Why-now / message generation (stubs in repo) |
| `ANTHROPIC_MODEL` | e.g. `claude-sonnet-4-20250514` |

---

## Environment file

Copy `.env.example` → `.env`. **Never submit `.env` in the zip.**

Minimum for **API-only judge demo:**

```bash
# No keys required — only local services
```

Minimum for **SMS demo:**

```bash
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...
```

Minimum for **voice demo:**

```bash
TWILIO_*   # as above
GEMINI_API_KEY=...
TUNNEL_LINK=https://xxxx.ngrok-free.app
```

---

## Service URL map (localhost)

```
M1_URL=http://localhost:8001
M4_URL=http://localhost:8004
M5_URL=http://localhost:8005
M6_URL=http://localhost:8006
M7_URL=http://localhost:8007
M8_URL=http://localhost:8008
M10_URL=http://localhost:8010
M11_URL=http://localhost:8011
```

---

## Security notes for submission

- All secrets via environment variables  
- `.gitignore` excludes `.env`, sessions, logs  
- Demo farmers use synthetic IDs (`GJ-014`, `GRW_00001`)  
- No production farmer PII in repository

---

## Accounts to create (team reference)

| Provider | URL | Used for |
|----------|-----|----------|
| Twilio | https://console.twilio.com | SMS, voice |
| Google AI Studio | https://aistudio.google.com | Gemini API key |
| ngrok | https://ngrok.com | Voice webhooks |
| Anthropic | https://console.anthropic.com | Future content gen |
| GitHub | Your repo | Source submission |
