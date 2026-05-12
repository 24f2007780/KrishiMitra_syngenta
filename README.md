# KrishiMitra AI

**Kisan Context Intelligence Engine** — a hackathon project for **SYNGENTA × IITM BS**, Track 1: *AI-powered agricultural marketing at scale*.

---

## The problem

Farmers often get **generic** or **untimely** messages. What they need is different:

- **Who** is this for? (this farmer, this crop, this place)
- **Why now?** (weather, pest risk, crop stage — not random promos)
- **What** should they do? (clear, advisory tone)
- **How** do they receive it? (SMS, WhatsApp, or voice — based on phone and network)
- **When** should it land? (sensible hours, less spam)

So the real problem is not “write marketing copy.” It is **decide whether to reach someone, then what to say, in their language, on the right channel, at the right time.**

---

## Our approach

We treat this as a **small decision pipeline** with a message at the end:

1. **Know the farmer** — profile, crops, language, device, how often we already messaged them.
2. **Know the situation** — weather and pest signals, plus where the crop is in the season (calendar).
3. **Score urgency** — math-based score and a **fatigue guard** so we do not spam.
4. **Pick products** — rule-based match to our product catalog (not random picks).
5. **Explain “why now”** — short reason in English and in the farmer’s language (AI helps here).
6. **Create content** — SMS (short), WhatsApp (longer + image idea text), or **voice script** for simple phones.
7. **Route and schedule** — choose channel from device/connectivity, pick send time in safe IST windows.
8. **Log and demo** — store what we “sent” and simulated outcomes; a **dashboard** shows the story for judges.

Many small **services** talk to each other; one **orchestrator** runs the full path for one farmer or many. Everyone shares the same **data shapes** (farmer + signals + stage + scores) so modules stay compatible.

---

## In one sentence

**The right message, for the right farmer, at the right moment** — before the agronomic window closes.

---

## Tech (short)

Python, FastAPI microservices, SQLite for farmers and delivery log, Pydantic for shared models, weather from Open-Meteo, Claude for multilingual explanations and message drafts, Streamlit for the demo UI.

---

## Detailed plan and architecture

For module list, APIs, day-by-day tasks, and diagrams, see the docs under the repo root:

- `.rajnish/plan/KRISHIMITRA_TECHNICAL_PLAN.md` — full technical plan  
- `.rajnish/system-architecture/OVERVIEW.md` — big-picture architecture  

---
