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

1. Load **profile** (crop, district, language, device, message history).  
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
  "farmer_contexts": [
    {
      "profile": {
        "farmer_id": "TN-100",
        "name": "Rajan Kumar",
        "age": 34,
        "phone": "+91-9876543000",
        "preferred_language": "Tamil",
        "state": "Tamil Nadu",
        "district": "Thanjavur",
        "village": "Papanasam",
        "acres": 1.6,
        "crops": ["rice"],
        "latitude": 10.7657,
        "longitude": 79.13,
        "device_type": "feature_phone",
        "connectivity": "2G",
        "whatsapp_enabled": true,
        "last_message_sent_at": "2026-04-27",
        "messages_received_last_30d": 5,
        "messages_opened_last_30d": 1,
        "preferred_contact_time": "morning",
        "linked_retailer_id": "RET-776",
        "linked_retailer_name": "Mahesh Babu Agro Agency"
      },
      "signals": {
        "district": "Thanjavur",
        "state": "Tamil Nadu",
        "humidity_7d_avg": 73.1,
        "rainfall_deviation_pct": -96.4,
        "temperature_anomaly": -0.7,
        "pest_risk_level": "high",
        "active_pest": "Fungal Blast",
        "weather_anomaly_flag": true
      },
      "crop_stage": {
        "confirmed_stage": "seed_treatment",
        "days_in_stage": 0,
        "vulnerability": "low",
        "days_to_next_stage": 15
      },
      "assembled_at": "2026-05-13T14:11:11.594965"
    },
    {
      "profile": {
        "farmer_id": "AP-101",
        "name": "Suresh Reddy",
        "age": 44,
        "phone": "+91-9876543001",
        "preferred_language": "Telugu",
        "state": "Andhra Pradesh",
        "district": "Guntur",
        "village": "Tenali",
        "acres": 6.8,
        "crops": ["cotton"],
        "latitude": 16.3141,
        "longitude": 80.4357,
        "device_type": "feature_phone",
        "connectivity": "offline",
        "whatsapp_enabled": true,
        "last_message_sent_at": "2026-04-12",
        "messages_received_last_30d": 5,
        "messages_opened_last_30d": 5,
        "preferred_contact_time": "afternoon",
        "linked_retailer_id": "RET-321",
        "linked_retailer_name": "Sunil Verma Agro Agency"
      },
      "signals": {
        "district": "Guntur Municipal Corporation",
        "state": "Andhra Pradesh",
        "humidity_7d_avg": 59.5,
        "rainfall_deviation_pct": -17.6,
        "temperature_anomaly": 1.2,
        "pest_risk_level": "medium",
        "active_pest": "Aphids",
        "weather_anomaly_flag": false
      },
      "crop_stage": {
        "confirmed_stage": "seed_treatment",
        "days_in_stage": 0,
        "vulnerability": "low",
        "days_to_next_stage": 15
      },
      "assembled_at": "2026-05-13T14:11:12.738492"
    },
    {
      "profile": {
        "farmer_id": "MH-102",
        "name": "Vijay Patil",
        "age": 38,
        "phone": "+91-9876543002",
        "preferred_language": "Marathi",
        "state": "Maharashtra",
        "district": "Jalna",
        "village": "Ambad",
        "acres": 3.4,
        "crops": ["rice"],
        "latitude": 19.8287,
        "longitude": 75.8927,
        "device_type": "feature_phone",
        "connectivity": "offline",
        "whatsapp_enabled": true,
        "last_message_sent_at": "2026-03-31",
        "messages_received_last_30d": 5,
        "messages_opened_last_30d": 3,
        "preferred_contact_time": "morning",
        "linked_retailer_id": "RET-487",
        "linked_retailer_name": "Ajay Meena Agro Agency"
      },
      "signals": {
        "district": "Jalna",
        "state": "Maharashtra",
        "humidity_7d_avg": 24.8,
        "rainfall_deviation_pct": -96.8,
        "temperature_anomaly": 6.8,
        "pest_risk_level": "high",
        "active_pest": "Bollworm",
        "weather_anomaly_flag": true
      },
      "crop_stage": {
        "confirmed_stage": "seed_treatment",
        "days_in_stage": 0,
        "vulnerability": "low",
        "days_to_next_stage": 15
      },
      "assembled_at": "2026-05-13T14:11:14.052743"
    }
  ]
}
```

## M8 — Product Ranker

```json
{
  "ranking_tests": [
    {
      "input": {
        "crop": "rice",
        "pest": "blight",
        "stage": "vegetative",
        "urgency": 0.5
      },
      "response": {
        "top_products": [
          "Vibrance RST",
          "Amistar Top"
        ],
        "match_reasons": [
          "Direct match for blight",
          "Direct match for blight"
        ]
      }
    },
    {
      "input": {
        "crop": "cotton",
        "pest": "aphid",
        "stage": "flowering",
        "urgency": 0.5
      },
      "response": {
        "top_products": [
          "Ridomil Gold GR",
          "Amistar Top"
        ],
        "match_reasons": [
          "Protects crop during critical flowering growth",
          "Protects crop during critical flowering growth"
        ]
      }
    },
    {
      "input": {
        "crop": "wheat",
        "pest": "rust",
        "stage": "vegetative",
        "urgency": 0.5
      },
      "response": {
        "top_products": [
          "Trivapro",
          "Miravis Ace"
        ],
        "match_reasons": [
          "Direct match for rust",
          "Protects crop during critical vegetative growth"
        ]
      }
    },
    {
      "input": {
        "crop": "rice",
        "pest": "none",
        "stage": "seed_treatment",
        "urgency": 0.5
      },
      "response": {
        "top_products": [
          "Vibrance RST",
          "Adage"
        ],
        "match_reasons": [
          "Specifically formulated for seed protection",
          "Ideal for your current seed_treatment stage"
        ]
      }
    }
  ]
}
```
