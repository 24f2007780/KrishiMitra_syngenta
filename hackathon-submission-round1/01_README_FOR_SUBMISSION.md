# KrishiMitra AI

**Kisan Context Intelligence Engine** — SYNGENTA × IITM BS Hackathon, Track 1: *AI-powered agricultural marketing at scale*.

---

## i. Project title and brief overview

**Title:** KrishiMitra AI — Context-First Farmer Outreach

**Overview:**  
Indian farmers often receive generic or mistimed marketing. KrishiMitra is a **decision system**, not a bulk message generator. For each farmer it assembles **who they are** (crop, district, language, device), **why outreach matters now** (weather, pest risk, growth stage), **which Syngenta-aligned product fits**, and **how to reach them** (SMS, WhatsApp, or AI voice call in Gujarati/Hindi/Bhojpuri/Tamil, etc.).

**Pipeline (implemented for demo):**

1. **Farmer profile** (M1) + **weather/pest signals** (M4) + **crop calendar** (M5)  
2. **Context assembler** (M6) → single `FarmerContext` object  
3. **Urgency scoring** (M7) + **product ranking** (M8)  
4. **Outbound delivery** — Twilio SMS (M10), WhatsApp Web (M11), Gemini live voice (Twilio Media Streams)

**Tagline:** *The right message, for the right farmer, at the right moment.*

*(Full technical detail: see `SOLUTION.pdf` / slides in this archive.)*

---

## ii. Team members and contact information

See **`TEAM_MEMBERS.md`** in this archive (same information as section e below).

| Role | Name | Email | Phone | Institution |
|------|------|-------|-------|-------------|
| [FILL IN] | [FILL IN] | [FILL IN] | [FILL IN] | IITM BS / [FILL IN] |
| [FILL IN] | [FILL IN] | [FILL IN] | [FILL IN] | [FILL IN] |

**Primary contact for judges:** [FILL IN NAME] — [FILL IN EMAIL] — [FILL IN PHONE]

---

## iii. Source code repository

**GitHub:** [FILL IN — e.g. https://github.com/your-org/KrishiMitra_syngenta]

**Main branch:** `main`  
**Key paths:**

| Path | Description |
|------|-------------|
| `farmer_service/`, `context_service/`, `product_service/` | Core microservices (M1, M6, M8) |
| `urgency_scorer/` | M7 urgency + engagement engine |
| `sms_service/`, `whatsapp_service/` | Context-based SMS / WhatsApp send |
| `twilio-voice-agent/` | Live voice calls (Gemini + Twilio) |
| `hackathon-submission-round1/` | This submission guide |
| `run_all.sh` | Start M1, M4, M5, M6, M8 locally |

---

## iv. Live deployment link

**[CHOOSE ONE]**

- **Option A — Not deployed (local demo):**  
  `N/A — Judges can run locally using SETUP_AND_RUN.md. Demo video shows full flow.`

- **Option B — ngrok / Cloud Run (if you deploy voice agent):**  
  `[FILL IN — e.g. https://xxxx.ngrok-free.app or Cloud Run URL]`

- **Option C — API docs only:**  
  `Local: http://127.0.0.1:8006/docs (M6), http://127.0.0.1:8008/docs (M8) after ./run_all.sh`

---

## v. Setup and execution instructions

See **`SETUP_AND_RUN.md`** in this archive (step-by-step install, seed DB, health checks, demo farmer Mayur).

**Quick start (judges with Python 3.11+):**

```bash
git clone [YOUR_REPO_URL]
cd KrishiMitra_syngenta
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add Twilio/Gemini keys only for SMS/voice demo
./run_all.sh
curl http://127.0.0.1:8006/context/GJ-014   # Mayur, Gujarat, cotton
```

**Demo video:** [FILL IN — YouTube or Google Drive link]  
**Solution document:** `SOLUTION.pdf` (included in submission archive)

---

## License / data

Hackathon submission — Syngenta IITM BS Track 1.  
Do not commit `.env` or API secrets. Demo uses synthetic farmer records when `dataset/growers.csv` is absent.
