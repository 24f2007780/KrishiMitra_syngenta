# Solution document / presentation slides — outline

Export as **PDF** (`SOLUTION.pdf`) and/or **PPTX** for the archive. Aim for **8–12 slides**, 5–8 min read.

Copy section titles directly into Google Slides / PowerPoint / Canva.

---

## Slide 1 — Title

- **KrishiMitra AI** — Kisan Context Intelligence Engine
- SYNGENTA × IITM BS | Track 1
- Team: [NAMES]
- Tagline: *Right farmer · Right moment · Right channel*

---

## Slide 2 — Problem

- Farmers get **generic**, **untimely** promos → low trust, wasted spend
- Marketing ignores: **who** (crop, language, device), **why now** (weather, pest, stage), **fatigue**
- Syngenta need: **scale with relevance**, not spam

**Visual:** Before/after — generic SMS vs contextual advisory

---

## Slide 3 — Solution (one diagram)

Use this flow (redraw in slides):

```text
Farmer DB + Weather + Calendar
         ↓
   FarmerContext (M6)
         ↓
 Urgency (M7) → Suppress? ──yes──→ Stop
         ↓ no
 Product Rank (M8) + Why-now (M9 planned)
         ↓
 SMS / WhatsApp / Voice (M10–M12)
         ↓
 Route + Schedule + Log (M13–M15)
```

**Key message:** Decision system first, message second.

---

## Slide 4 — What we built (Round 1)

| Layer | Status | Evidence |
|-------|--------|----------|
| M1 Farmer DB | ✅ Demo farmers + API | `/farmers`, seed endpoint |
| M4–M6 Context | ✅ Live | `/context/GRW_00001 ` |
| M7 Urgency | ✅ Engine + SHAP explain | `urgency_scorer/` |
| M8 Product rank | ✅ 12 products, ranked | `/products/GRW_00001 ` |
| M10 SMS | ✅ Context JSON → Twilio | `send_farmer_sms.py` |
| M11 WhatsApp | ✅ Neonize Web | `send_farmer_whatsapp.py` |
| Voice | ✅ Gemini Live + Twilio | `twilio-voice-agent` |
| M16 Orchestrator | 🔜 Next phase | Planned |

---

## Slide 5 — FarmerContext (technical spine)

- Single JSON object per farmer per run
- Fields: profile, signals (humidity, pest), crop_stage
- **Example:** Mayur, Anand, Gujarat, cotton, Gujarati
- Screenshot: `curl .../context/GRW_00001 ` (paste terminal output)

---

## Slide 6 — Intelligence

**M7 — Urgency (rules + ML engagement)**  
- Agronomic urgency: pest, weather anomaly, crop vulnerability  
- Fatigue guard: too many messages → suppress  
- Output: score 0–1, recommended channel  

**M8 — Product rank**  
- Crop + pest + stage + catalog  
- Explainable `match_reasons` (not black box)  
- Screenshot: top products for Mayur

---

## Slide 7 — Multilingual outreach

- **Context-first scripts:** `intro_script`, `sms_script`, `whatsapp_script` in farmer language
- **Voice:** Gemini speaks Gujarati/Hindi after personalized `<Say>` intro
- **Channels:** SMS (160 chars), WhatsApp (rich text), voice (feature phones)

Demo farmer: **Mayur**, Boriavi, Anand — cotton, whitefly advisory

---

## Slide 8 — Architecture

- FastAPI microservices, ports 8001–8008
- SQLite `master.db`, shared Pydantic models (`shared/models.py`)
- Integrations: Open-Meteo, Twilio, Gemini Live API
- **Not** a monolith — hackathon-friendly modules M1–M17

Small architecture diagram from `.rajnish/system-architecture/OVERVIEW.md` if available.

---

## Slide 9 — Demo walkthrough (for video alignment)

1. `./run_all.sh` → health checks  
2. Context for `GJ-014`  
3. Product recommendations  
4. Send SMS / place voice call to Mayur  
5. Farmer hears Gujarati advisory

---

## Slide 10 — Impact & differentiation

| vs generic CRM | KrishiMitra |
|----------------|-------------|
| Same message to all | Per-farmer context |
| Send always | Suppress when fatigued |
| Product push | Ranked + reason codes |
| One channel | SMS / WA / voice by device |

**Scale path:** M16 batch orchestrator, Streamlit dashboard (M17), full growers.csv

---

## Slide 11 — Roadmap (if selected for next round)

- Wire M6 live weather → richer pest signals  
- M9 Claude “why now” bilingual copy  
- M16 orchestrator + M17 judge dashboard  
- Production: Meta WhatsApp Cloud API, Syngenta catalog sync  

---

## Slide 12 — Team & links

- Team table (from `02_TEAM_MEMBERS.md`)
- GitHub: [URL]
- Demo video: [URL]
- Thank you / Q&A

---

## Export checklist

- [ ] PDF named `SOLUTION.pdf` in submission zip  
- [ ] File size &lt; 20 MB (compress images)  
- [ ] Fonts readable when projected  
- [ ] No API keys on slides
