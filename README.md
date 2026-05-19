# KrishiMitra AI

**Kisan Context Intelligence Engine** — hackathon project for **SYNGENTA × IITM BS**, Track 1: *AI-powered agricultural marketing at scale*.

---

## Problem

Farmers often get **generic** or **untimely** messages. What actually matters:

- **Who** — this farmer, this crop, this place  
- **Why now** — weather, pest risk, crop stage — not random promos  
- **What to do** — clear, advisory tone  
- **How** — SMS, WhatsApp, or voice — depends on phone and network  
- **When** — sensible hours, not spam  

So we are not building “another content generator.” We are building a **small decision system** that only then outputs a message: *should we reach this person now, and if yes, how?*

---

## Solution (in plain words)

We combine **farmer data**, **weather/pest signals**, and a **crop calendar** into one picture. We **score how urgent** it is and **block sending** if the farmer was messaged too recently or too often. If we still send, we **match products**, use AI for a **“why now”** line and for **SMS / WhatsApp / voice** text, then **pick channel and time**, and **log** everything for the demo.

**One line:** *The right message, for the right farmer, at the right moment* — before the agronomic window closes.

---

## How we solve it (one farmer, step by step)

1. Load **profile** (crop, district, preferred_language, device, message history).  
2. Load **weather + pest risk** for that district.  
3. Load **growth stage** for their crop this month.  
4. **Merge** into one object (**FarmerContext**) — same shape for every service.  
5. **Urgency score** + **suppress** if fatigue rules say “do not send.”  
6. If not suppressed: **rank products** from the catalog (rules, not random).  
7. AI writes **why now** (English + farmer’s language).  
8. AI writes **SMS**, **WhatsApp** (+ short image idea text), **voice script**.  
9. **Router** picks SMS vs WhatsApp vs voice from device and connectivity.  
10. **Timer** picks send time in allowed IST windows.  
11. **Delivery log** stores the row; the **dashboard** can simulate outcomes.

Many **small APIs** (modules) do one job each; **one orchestrator** runs the chain for one farmer or a batch.

---

## Modules — what each part does

| # | Name | What it does |
|---|------|----------------|
| **M1** | Farmer DB | Stores farmers; get by id or list; seed demo data (SQLite). |
| **M2** | Product catalog | Products linked to crop/pest/stage; APIs to query. |
| **M3** | Shared models | **No HTTP** — shared Pydantic types so every module uses the same fields. Build this first. |
| **M4** | Weather + pest | Weather API + pest file → risk-style signal bundle. |
| **M5** | Crop calendar | State + crop + month → growth stage and vulnerability (JSON lookup). |
| **M6** | Context assembler | Calls M1 + M4 + M5 → builds **FarmerContext** (with fallback if weather fails). |
| **M7** | Urgency scorer | Score 0–1 + **suppress** when recency / message count says stop. |
| **M8** | Product ranker | Top products for this context (rules from catalog). |
| **M9** | Why-now explainer | AI: one clear “why now” in English + local language (template if API fails). |
| **M10** | SMS generator | AI: very short SMS (length limit), local language. |
| **M11** | WhatsApp generator | AI: longer text + one sentence describing an image idea (no real image file). |
| **M12** | Voice script | AI: spoken-style script for farmers on simple phones. |
| **M13** | Channel router | Chooses SMS vs WhatsApp vs voice from device + network (+ flags for high urgency). |
| **M14** | Timing engine | Send time inside allowed IST windows (+ prefs / holidays). |
| **M15** | Delivery log | Saves each send + outcomes for stats and dashboard. |
| **M16** | Orchestrator | Runs the full pipeline per farmer; one failure does not kill the whole batch. |
| **M17** | Dashboard | Streamlit UI for demo: farmer, score, messages, run campaign, fake outcomes. |

Each service also exposes **`GET /health`** so the orchestrator can check that things are up.

---

## Tech (short)

Python 3.11+, **FastAPI** microservices, **SQLite** (farmers + delivery log), **Pydantic** (shared models), **Open-Meteo** (weather), **Claude** (multilingual explanations and message drafts), **Streamlit** (demo dashboard).

---

## M6 — Context Assembler
```json
{
    "profile": {
        "farmer_id": "GRW_00005",
        "name": "Grower GRW_00005",
        "age": 26,
        "phone": "+91-9000000005",
        "preferred_language": "Hindi",
        "state": "Uttar Pradesh",
        "district": "Kanpur Nagar",
        "village": "Kanpur_Nagar_T124",
        "acres": 1.33,
        "crops": [
            "wheat"
        ],
        "latitude": 26.8467,
        "longitude": 80.9462,
        "device_type": "android",
        "connectivity": "4G",
        "whatsapp_enabled": True,
        "last_message_sent_at": None,
        "messages_received_last_30d": 0,
        "messages_opened_last_30d": 0,
        "preferred_contact_time": "morning",
        "linked_retailer_id": "RET-204",
        "linked_retailer_name": "Kanpur Nagar Agro Center"
    },
    "signals": {
        "district": "Lucknow",
        "state": "Uttar Pradesh",
        "humidity_7d_avg": 31.5,
        "rainfall_deviation_pct": -100.0,
        "temperature_anomaly": 4.1,
        "pest_risk_level": "low",
        "active_pest": "None",
        "weather_anomaly_flag": True
    },
    "crop_stage": {
        "confirmed_stage": "vegetative",
        "days_in_stage": 0,
        "vulnerability": "low",
        "days_to_next_stage": 30
    },
    "assembled_at": "2026-05-18T18: 18: 57.287747"
}
```

## M8 — Product Ranker

```json
{
  "grower_id": "GRW_00001",
  "crop": "wheat",
  "pest": "rust",
  "top_products": [
    {
      "product_name": "Score 250 EC",
      "match_score": 0.746,
      "confidence": 0.7,
      "match_reasons": [
        "Registered for wheat crop protection",
        "Effective at general growth stage",
        "Preventive protection — ideal for proactive care",
        "Systemic action — absorbed and translocated in plant"
      ],
      "score_breakdown": {
        "efficacy": 0.98,
        "adoption": 0.5,
        "availability": 0.62,
        "moa_group": "FRAC-3",
        "treatment_intent": [
          "preventive",
          "curative"
        ],
        "price_tier": "mid",
        "weights_used": {
          "efficacy": 0.44,
          "adoption": 0.27,
          "availability": 0.29
        }
      }
    },
    {
      "product_name": "Amistar 250 SC",
      "match_score": 0.729,
      "confidence": 0.7,
      "match_reasons": [
        "Registered for wheat crop protection",
        "Targets rust — efficacy rating 91%",
        "Effective at general growth stage",
        "Preventive protection — ideal for proactive care",
        "Systemic action — absorbed and translocated in plant"
      ],
      "score_breakdown": {
        "efficacy": 0.982,
        "adoption": 0.5,
        "availability": 0.56,
        "moa_group": "FRAC-11",
        "treatment_intent": [
          "preventive",
          "curative"
        ],
        "price_tier": "premium",
        "weights_used": {
          "efficacy": 0.44,
          "adoption": 0.27,
          "availability": 0.29
        }
      }
    },
    {
      "product_name": "Kavach 75 WP",
      "match_score": 0.622,
      "confidence": 0.66,
      "match_reasons": [
        "Targets rust — efficacy rating 84%",
        "Effective at general growth stage",
        "Preventive protection — ideal for proactive care"
      ],
      "score_breakdown": {
        "efficacy": 0.718,
        "adoption": 0.5,
        "availability": 0.59,
        "moa_group": "FRAC-M5",
        "treatment_intent": [
          "preventive"
        ],
        "price_tier": "low",
        "weights_used": {
          "efficacy": 0.44,
          "adoption": 0.27,
          "availability": 0.29
        }
      }
    }
  ],
  "not_recommended": [
    {
      "product_name": "Tilt 250 EC",
      "not_ranked_higher_because": [
        "Same MoA group (FRAC-3) already represented in recommendations"
      ]
    },
    {
      "product_name": "Alto 5 SC",
      "not_ranked_higher_because": [
        "Same MoA group (FRAC-3) already represented in recommendations"
      ]
    },
    {
      "product_name": "Movondo",
      "not_ranked_higher_because": [
        "Lower combined score than selected alternatives"
      ]
    }
  ],
  "resistance_advisory": null,
  "fallback_used": false,
  "model_version": "m8-hybrid-v1"
}
```
