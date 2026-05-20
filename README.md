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

# API Documentation


All services expose a common health-check endpoint:

```http id="ykhh8u"
GET /health
```

---
## M1 — Farmer DB `http://localhost:8001/farmer/GRW_00001`

| Port | Method | URL                   | Input                  | Output                                  |
| ---- | ------ | --------------------- | ---------------------- | --------------------------------------- |
| 8001 | GET    | `/farmer/{grower_id}` | `grower_id` path param | Farmer profile (`FarmerProfile`)        |
| 8001 | GET    | `/farmers`            | None                   | List of all farmers                     |
| 8001 | POST   | `/farmers/seed`       | None                   | Seeder execution status + seeded counts |

```json
{
  "grower_id": "GRW_00001",
  "name": "Rajan Kumar",
  "grower_age": 67,
  "phone": "+91-9000000000",
  "preferred_language": "Hindi",
  "state": "Rajasthan",
  "district": "Bharatpur",
  "tehsil": "Bharatpur_T023",
  "grower_farm_size": 3.54,
  "crops": [
    "wheat"
  ],
  "latitude": 27.0238,
  "longitude": 74.2179,
  "device_type": "android",
  "connectivity": "4G",
  "whatsapp_enabled": true,
  "last_message_sent_at": null,
  "messages_received_last_30d": 1,
  "messages_opened_last_30d": 0,
  "preferred_contact_time": "evening",
  "linked_retailer_id": "RET-200",
  "linked_retailer_name": "Bharatpur Agro Center",
  "urgency_score": 0.52,
  "recommended_channel": "whatsapp"
}

```

## M4 — Weather + Pest Signals `http://localhost:8004/signals/weather?lat=13.00663&lon=80.244193`

| Port | Method | URL                | Input                     | Output                                  |
| ---- | ------ | ------------------ | ------------------------- | --------------------------------------- |
| 8004 | GET    | `/signals/weather` | `lat`, `lon` query params | Weather + pest signals (`SignalBundle`) |
| 8004 | GET    | `/debug/weather`   | Optional debug parameters | Raw weather diagnostics                 |

```json
{
  "district": "Chennai Corporation",
  "state": "Tamil Nadu",
  "humidity_7d_avg": 56.3,
  "rainfall_deviation_pct": 659.8,
  "weather_anomaly": 1,
  "pest_risk": 0.2,
  "active_pest": "None",
  "weather_anomaly_flag": true
}
```

## M5 — Crop Calendar `http://localhost:8005/calendar?state=Tamil+Nadu&crop=blackgram`


| Port | Method | URL         | Input                        | Output                                               |
| ---- | ------ | ----------- | ---------------------------- | ---------------------------------------------------- |
| 8005 | GET    | `/`         | None                         | Crop calendar service metadata                       |
| 8005 | GET    | `/calendar` | `state`, `crop` query params | Crop stage + MSP + recommendations (`CropStageInfo`) |

```json
{
  "state": "Maharashtra",
  "crop": "cotton",
  "month": "may",
  "stage": "seed_treatment",
  "crop_vulnerability": 0.2,
  "days_to_next": 15,
  "recommendations": [
    "Treat seeds with Imidacloprid or Thiamethoxam (7.5 g/kg), Thiram or Captan (3 g/kg), Azotobacter (25 g/kg), and PSB (20 g/kg)."
  ],
  "msp_rs_quintal": "7710.00",
  "today_price_rs_quintal": "8255.09",
  "today_arrival_metric_tonnes": "1928.91"
}
```
MSP Minimum Support Price using https://api.agmarknet.gov.in/v1/dashboard-data/

## M6 — Context Assembler `http://localhost:8006/context/GRW_00005`


| Port | Method | URL                    | Input                  | Output                                           |
| ---- | ------ | ---------------------- | ---------------------- | ------------------------------------------------ |
| 8006 | GET    | `/context/{grower_id}` | `grower_id` path param | Fully assembled farmer context (`FarmerContext`) |
| 8006 | POST   | `/context/batch`       | List of grower IDs     | Batch assembled farmer contexts                  |

```json
{
  "profile": {
    "grower_id": "GRW_00005",
    "name": "Ramesh Kumar",
    "grower_age": 26,
    "phone": "+91-9000000004",
    "preferred_language": "Hindi",
    "state": "Uttar Pradesh",
    "district": "Kanpur Nagar",
    "tehsil": "Kanpur_Nagar_T124",
    "grower_farm_size": 1.33,
    "crops": [
      "wheat"
    ],
    "latitude": 26.8467,
    "longitude": 80.9462,
    "device_type": "android",
    "connectivity": "4G",
    "whatsapp_enabled": true,
    "last_message_sent_at": null,
    "messages_received_last_30d": 1,
    "messages_opened_last_30d": 0,
    "preferred_contact_time": "morning",
    "linked_retailer_id": "RET-204",
    "linked_retailer_name": "Kanpur Nagar Agro Center",
    "urgency_score": 0.52,
    "recommended_channel": "whatsapp"
  },
  "signals": {
    "district": "Kanpur Nagar",
    "state": "Uttar Pradesh",
    "humidity_7d_avg": 32.1,
    "rainfall_deviation_pct": -100,
    "weather_anomaly": 0.5,
    "pest_risk": 0.2,
    "active_pest": "None",
    "weather_anomaly_flag": true
  },
  "crop_stage": {
    "confirmed_stage": "vegetative",
    "days_in_stage": 0,
    "crop_vulnerability": 0.2,
    "days_to_next_stage": 30
  },
  "assembled_at": "2026-05-20T06:00:13.953183"
}
```

## M7 — Urgency Score gives `http://localhost:8007/score/GRW_05989` with farmer context gives a score (0-1)

| Port | Method | URL        | Input                     | Output                                               |
| ---- | ------ | ---------- | ------------------------- | ---------------------------------------------------- |
| 8007 | POST   | `/score`   | `FarmerContext` JSON body | Urgency score + suppression + channel recommendation |
| 8007 | POST   | `/explain` | `FarmerContext` JSON body | Why-now explanation + rationale                      |

```json
{
  "grower_id": "GRW_05989",
  "urgency_score": 0.22,
  "urgency_components": {
    "pest_risk_term": 0.08,
    "weather_anomaly_term": 0,
    "crop_vulnerability_term": 0.04,
    "recency_term": 0.1,
    "recency_penalty_raw": 0,
    "weights_source": "default",
    "weights_used": {
      "pest_risk": 0.4,
      "weather_anomaly": 0.3,
      "crop_vulnerability": 0.2,
      "communication_window": 0.1
    },
    "top_factors": [
      "Communication Window Available",
      "High Pest Outbreak Risk",
      "Critical Crop Stage Vulnerability"
    ]
  },
  "engagement_score": 0.15,
  "engagement_components": {
    "calibrated_probability": null,
    "engagement_scaled": 0.15,
    "top_factors": [
      "Zero message opens (low responsiveness)",
      "Baseline engagement estimate"
    ],
    "model_used": false
  },
  "intervention_priority": 0.21,
  "recommended_channel": "whatsapp",
  "suppress": false,
  "suppress_reason": null,
  "top_factors": [
    "Communication Window Available",
    "High Pest Outbreak Risk",
    "Critical Crop Stage Vulnerability"
  ],
  "confidence": 0.5,
  "expected_intervention_value": -0.017,
  "model_version": "m7-hybrid-v2"
}
```
## M8 — Product Ranker `http://localhost:8002/products/GRW_00012`

| Port | Method | URL                     | Input                   | Output                                 |
| ---- | ------ | ----------------------- | ----------------------- | -------------------------------------- |
| 8002 | POST   | `/rank`                 | `RankRequest` JSON body | Ranked products (`RankResponse`)       |
| 8002 | GET    | `/products/{grower_id}` | `grower_id` path param  | Personalized agronomic recommendations |

```json
{
  "grower_id": "GRW_00012",
  "crop": "wheat",
  "pest": "rust",
  "top_products": [
    {
      "product_name": "Tilt 250 EC",
      "match_score": 0.753,
      "confidence": 0.7,
      "match_reasons": [
        "Registered for wheat crop protection",
        "Effective at general growth stage",
        "Preventive protection — ideal for proactive care",
        "Systemic action — absorbed and translocated in plant"
      ],
      "score_breakdown": {
        "efficacy": 0.972,
        "adoption": 0.5,
        "availability": 0.65,
        "moa_group": "FRAC-3",
        "treatment_intent": [
          "preventive",
          "curative"
        ],
        "price_tier": "low",
        "weights_used": {
          "efficacy": 0.44,
          "adoption": 0.27,
          "availability": 0.29
        }
      }
    },
    {
      "product_name": "Amistar 250 SC",
      "match_score": 0.705,
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
        "availability": 0.47,
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
      "match_score": 0.64,
      "confidence": 0.66,
      "match_reasons": [
        "Targets rust — efficacy rating 84%",
        "Effective at general growth stage",
        "Preventive protection — ideal for proactive care"
      ],
      "score_breakdown": {
        "efficacy": 0.718,
        "adoption": 0.5,
        "availability": 0.65,
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
      "product_name": "Score 250 EC",
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
      "product_name": "Cruiser 350 FS",
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


## M16 — Campaign Orchestrator `http://localhost:8008/predict/GRW_05989` 


| Port | Method | URL                    | Input                             | Output                                 |
| ---- | ------ | ---------------------- | --------------------------------- | -------------------------------------- |
| 8008 | POST   | `/predict`             | `FarmerContext` or grower profile | Campaign orchestration prediction      |
| 8008 | GET    | `/predict/{grower_id}` | `grower_id` path param            | Personalized campaign strategy         |
| 8008 | POST   | `/explain`             | Campaign prediction JSON          | Human-readable orchestration reasoning |

```json
{
  "grower_id": "GRW_05989",
  "segment": "offline_only",
  "segment_confidence": 0.8,
  "receptivity_score": 0.15,
  "recommended_formats": [
    {
      "format": "field_demo",
      "predicted_engagement": 0.22,
      "confidence": 0.7,
      "reasoning": "In-person demonstration builds trust for new products"
    },
    {
      "format": "voice_ivr",
      "predicted_engagement": 0.12,
      "confidence": 0.7,
      "reasoning": "Voice in local language overcomes literacy barriers"
    },
    {
      "format": "sms_short",
      "predicted_engagement": 0.06,
      "confidence": 0.7,
      "reasoning": "Reaches keypad users; concise actionable message"
    }
  ],
  "best_day_of_week": "Saturday",
  "best_time_window": "10:00 AM–12:00 PM",
  "fatigue_risk": 0.65,
  "creative_suggestions": [
    "Prioritize voice/IVR in local language over digital formats",
    "Coordinate with field rep visit for in-person demonstration",
    "⚠️ High fatigue risk — reduce frequency or switch to high-value content only",
    "Low receptivity predicted — consider escalating to field visit or voice call"
  ],
  "model_version": "campaign-receptivity-v1"
}

```

# Core Microservice Mapping

| Module | Port | Responsibility                                  |
| ------ | ---- | ----------------------------------------------- |
| M1     | 8001 | Farmer profile database                         |
| M4     | 8004 | Weather + pest intelligence                     |
| M5     | 8005 | Crop calendar + MSP                             |
| M6     | 8006 | Unified farmer context assembly                 |
| M7     | 8007 | Urgency scoring + explainability                |
| M8     | 8002 | Agronomic product ranking                       |
| M16    | 8008 | Campaign orchestration + receptivity prediction |

# Running the Services

To manage the microservices during local development or testing, use the following commands in the project root:

### Start All Microservices
Run the startup script to launch all active microservice APIs (M1, M2, M4, M5, M6, M7, M8, M16) in the background:
```bash
./run_all.sh
```

### Stop All Microservices
Run the teardown script to terminate all active `uvicorn` instances:
```bash
./stop_all.sh
```

M8 PRODUCT RANKER — PERFORMANCE EVALUATION

    POS transactions: 235042
    Growers: 6000
    Products in catalog: 12
    Valid evaluation queries: 37540
    Unique districts: 33
    Unique products purchased: 12
    Completed 2000 evaluations.

    ✓ wheat + rust → expects Score 250 EC: FOUND
    ✓ wheat + weeds → expects Topik 15 WP: FOUND
    ✓ potato + blight → expects Kavach 75 WP: FOUND
    ✓ chickpea + aphid → expects Actara 25 WG: FOUND
    ✓ mustard + fungal → expects Score 250 EC: FOUND

    Coherence: 5/5 domain rules satisfied


    Exact Hit Rate @2:     0.228 (random=0.173, lift=1.3×)
    Agronomic Hit Rate @2: 0.647 (random=0.349, lift=1.9×)
    MoA-aware Hit Rate @2: 0.466
    Functional Recall @2:  0.831
    Exact Hit Rate @5:     0.664
    Agronomic Hit Rate @5: 0.861
    MRR:                   0.279
    Coverage:              100%
    MoA Diversity:         0.92
    Coherence:             5/5

  ✓ Good catalog coverage — not stuck recommending same products.
  ✓ Good MoA diversity — resistance management working.