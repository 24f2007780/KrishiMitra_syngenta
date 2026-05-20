# Setup and execution instructions (for judges)

Target: run the **core intelligence pipeline** locally in ~10 minutes. SMS/voice need extra API keys.

**Requirements:** Linux/macOS/WSL, Python **3.11+** (3.14 tested), `git`, `curl`.

---

## 1. Clone and install

```bash
git clone [YOUR_GITHUB_REPO_URL]
cd KrishiMitra_syngenta

python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

---

## 2. Environment (optional for API-only demo)

```bash
cp .env.example .env
```

| Key | Needed for |
|-----|------------|
| *(none)* | M1, M4, M5, M6, M8 health + context + rank |
| `TWILIO_*` | SMS (`sms_service`) |
| `GEMINI_API_KEY`, `TUNNEL_LINK` | Voice calls (`twilio-voice-agent`) |
| WhatsApp | `pip install -r whatsapp_apps/requirements.txt` + QR login |

---

## 3. Bootstrap database

```bash
python scripts/bootstrap_db.py
```

Expected:

- `Seeded 12 products` (or “already present”)
- `Seeded 5 farmers` (demo set including **GJ-014 Mayur**)

---

## 4. Start microservices

```bash
./run_all.sh
```

Services:

| Port | Module | Health |
|------|--------|--------|
| 8001 | M1 Farmers | `curl http://127.0.0.1:8001/health` |
| 8004 | M4 Weather | 8004/health |
| 8005 | M5 Calendar | 8005/health |
| 8006 | M6 Context | 8006/health |
| 8008 | M8 Product ranker | 8008/health → `"catalog_size":12` |

Stop all: `./stop_all.sh`

---

## 5. Demo API calls (Mayur — Gujarat, cotton)

```bash
# List farmers
curl http://127.0.0.1:8001/farmers

# Assembled context (profile + weather + crop stage)
curl http://127.0.0.1:8006/context/GJ-014 | python -m json.tool

# Top product recommendations
curl http://127.0.0.1:8008/products/GJ-014 | python -m json.tool
```

---

## 6. Outbound channels (optional)

### SMS (Twilio)

```bash
cd twilio-voice-agent
pip install httpx twilio python-dotenv   # if not in main venv
python scripts/send_farmer_sms.py --json config/farmer_mayur.example.json --preview
python scripts/send_farmer_sms.py --json config/farmer_mayur.example.json
```

### Voice (Gemini + Twilio + ngrok)

```bash
cd twilio-voice-agent
./start.sh
# separate terminal:
python scripts/krishimitra_call.py --json config/farmer_mayur.example.json
```

See `twilio-voice-agent/RUN_README.md`.

### WhatsApp

```bash
pip install -r whatsapp_apps/requirements.txt
python -m whatsapp_apps.web.app login    # scan QR once
cd twilio-voice-agent
python scripts/send_farmer_whatsapp.py --json config/farmer_mayur.example.json
```

---

## 7. Troubleshooting

| Issue | Fix |
|-------|-----|
| Empty `/farmers` | `curl -X POST "http://127.0.0.1:8001/farmers/seed"` or `python scripts/bootstrap_db.py` |
| M8 `catalog_size: 0` | Restart after `bootstrap_db.py`; check `product-catalog/canonical_products.json` |
| Port in use | `./stop_all.sh` then `./run_all.sh` |
| Voice “application error” | Restart `./start.sh`; update ngrok URL in `.env` |

---

## 8. Run tests (optional)

```bash
python test_m6.py
python test_m8.py
```
