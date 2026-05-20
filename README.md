# KrishiMitra AI

**Kisan Context Intelligence Engine** — SYNGENTA × IITM BS Hackathon, Track 1: *AI-powered agricultural marketing at scale*.

---

## i. Project Title and Overview

**Title:** KrishiMitra AI — Context-First Farmer Outreach

**Overview:**  
Indian farmers often receive generic or mistimed marketing. KrishiMitra is a context-first agricultural decision and outreach orchestration engine. It dynamically aggregates multi-dimensional farmer context (crop calendars, local weather anomalies, and pest risk signals) to determine if outreach is needed, rank relevant products, and deliver personalized multilingual advice via Twilio SMS, WhatsApp, and interactive Gemini Live voice agent calls.

**Pipeline Workflow:**
1. **Context Assembly:** Aggregates Farmer Profile (M1), Weather/Pest Signals (M4), and Crop Calendar (M5) into a unified `FarmerContext`.
2. **Scoring & Suppression:** Runs Urgency Scoring (M7) and evaluates communication fatigue rules.
3. **Product Selection:** Performs personalized Product Ranking (M8) based on agronomic needs.
4. **Outbound Delivery:** Delivers localized audio scripts or text alerts via Twilio SMS (M10), WhatsApp Web (M11), and Gemini Live voice calls.

**Tagline:** *The right message, for the right farmer, at the right moment — before the agronomic window closes.*

*(Full technical details can be found in `SOLUTION.pdf` and accompanying slides in this archive.)*

---

## ii. Team Members and Contact Information

See **`TEAM_MEMBERS.md`** in this archive for detailed contributions.

| Role | Name | Email | Phone | Institution |
|---|---|---|---|---|
| Backend (REST APIs) | Yashvi Upadhyay | [24f2007780@ds.study.iitm.ac.in](mailto:24f2007780@ds.study.iitm.ac.in) | +91 7709669004 | IITM BS |
| DevOps: Voice call, SMS, WhatsApp & Planner | Rajnish Kumar | [22f2000625@ds.study.iitm.ac.in](mailto:22f2000625@ds.study.iitm.ac.in) | +91 9150740978 | IITM BS |
| Machine Learning | Mayur H. Doshi | [24f1000027@ds.study.iitm.ac.in](mailto:24f1000027@ds.study.iitm.ac.in) | +91 9152155576 | IITM BS |
| Backend | Agrim Srivastava | [23f3002782@ds.study.iitm.ac.in](mailto:23f3002782@ds.study.iitm.ac.in) | +91 8081037827 | IITM BS |
| Machine Learning & Research | Tarang Jhaveri | [23f2004661@ds.study.iitm.ac.in](mailto:23f2004661@ds.study.iitm.ac.in) | +91 9284709410 | IITM BS |

**Primary Contact for Judges:** Yashvi Upadhyay — [24f2007780@ds.study.iitm.ac.in](mailto:24f2007780@ds.study.iitm.ac.in) — +91 7709669004

---

## iii. Source Code Repository & Key Paths

**GitHub Repository:** [https://github.com/24f2007780/KrishiMitra_syngenta](https://github.com/24f2007780/KrishiMitra_syngenta)  
**Main Branch:** `main`

### Repository Key Paths:

| Path | Description |
|------|-------------|
| `farmer_service/` | Farmer Profile management service (M1) |
| `weather_service/` | Weather & pest risk intelligence harvester (M4) |
| `calendar_service/` | Crop stages, recommendations & MSP lookup (M5) |
| `context_service/` | Unified farmer context assembler (M6) |
| `urgency_scorer/` | Urgency calculations and suppression engine (M7) |
| `product_service/` | Personalized agronomic product ranking (M8) |
| `campaign_receptivity_engine/` | Campaign scheduling & channel receptivity models (M16) |
| `twilio-voice-agent/` | Gemini Live voice agent (Twilio Media Streams) & Call Dashboard (M17) |
| `whatsapp_apps/`, `whatsapp_service/` | WhatsApp Web delivery integration |
| `run_all.sh` / `stop_all.sh` | Orchestration scripts to start/stop all microservices |
| `hackathon-submission-round1/` | Judges' checklist, submission runbook, and configurations |

---

## iv. Setup & Execution Instructions

Detailed installation steps are available in **`SETUP_AND_RUN.md`**.

### Quick Start (Judges with Python 3.11+):

```bash
# Clone the repository
git clone https://github.com/24f2007780/KrishiMitra_syngenta.git
cd KrishiMitra_syngenta

# Create virtual environment and install core dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create environment configuration (add API keys for Twilio and Gemini Voice Agent)
cp .env.example .env

# Bootstrap local database with canonical products and farmers
python scripts/bootstrap_db.py

# Launch all active microservices (Ports 8001, 8004, 8005, 8006, 8007, 8008, 8009)
./run_all.sh

# Verify a grower context (Demo Grower Mayur, Gujarat, cotton)
curl http://127.0.0.1:8006/context/GRW_00001
```

**Demo Video Link:** *[FILL IN — YouTube or Google Drive Link]*  
**Solution Document:** `SOLUTION.pdf` (included in submission archive)

---

## v. Component Modules Overview

Each microservice exposes a standard **`GET /health`** health check endpoint.

| Module | Type / Port | Responsibility & Details |
|---|---|---|
| **M1** | `8001` (Service) | **Farmer DB:** Stores farmer profiles, credentials, languages, and contact logs in SQLite. |
| **M2** | Database Catalog | **Product Catalog:** Canonical mapping of Syngenta products to crops, growth stages, and pests. |
| **M3** | Shared Models | **No HTTP Port:** Shared Pydantic data schemas used across all services to guarantee structure safety. |
| **M4** | `8004` (Service) | **Weather + Pest:** Harvester API for Open-Meteo current anomalies & local pest risks. |
| **M5** | `8005` (Service) | **Crop Calendar:** Rules mapping state/crop/month to vulnerability indices, growth stages, and Agmarknet MSP. |
| **M6** | `8006` (Service) | **Context Assembler:** Orchestrator aggregating profile, signal, and calendar details into a `FarmerContext`. |
| **M7** | `8007` (Service) | **Urgency Scorer:** Evaluates risk terms, calculates priority, and flags communication fatigue suppressions. |
| **M8** | `8008` (Service) | **Product Ranker:** Personalized recommendation engine filtering catalog products using agronomic rules. |
| **M9** | AI Engine (Anthropic) | **Why-Now Explainer:** Generates clear reasonings in native language templates. |
| **M10** | Outbound Service | **SMS Generator:** Formats character-limited SMS texts in native languages. |
| **M11** | Outbound Service | **WhatsApp Generator:** Formats WhatsApp rich texts and image prompts. |
| **M12** | Voice Agent | **Voice Script:** Spoken-style script templates for Interactive Voice Response (IVR). |
| **M13** | Core Engine | **Channel Router:** Dynamic logic routing calls or texts based on device types and priority. |
| **M14** | Core Engine | **Timing Engine:** Schedules deliveries to avoid holiday disturbances and align with allowed IST windows. |
| **M15** | Database Log | **Delivery Log:** Event-store tracking all sent alerts, deliveries, and farmer engagement statuses. |
| **M16** | `8009` (Service) | **Campaign Orchestrator:** Machine learning engine mapping farmer receptivity, timing preferences, and fatigue risks. |
| **M17** | `8000` (Web UI) | **Call Dashboard:** Live monitoring interface for Gemini Voice calls and transcripts in `twilio-voice-agent`. |

---

## vi. API Documentation

All services expose a common health check endpoint: `GET /health`.

---

## M1 — Farmer DB `http://localhost:8001/farmer/GRW_00001`

| Method | Endpoint | Description | Input | Output |
|---|---|---|---|---|
| **GET** | `/farmer/{grower_id}` | Retrieve individual farmer profile | `grower_id` path param | `FarmerProfile` JSON |
| **GET** | `/farmers` | List all growers in DB | None | List of `FarmerProfile` JSONs |
| **POST** | `/farmers/seed` | Seed SQLite DB with demo farmers | None | Seeder statistics |

<details>
<summary><b>View Example Response JSON (GET <code>/farmer/GRW_00001</code>)</b></summary>

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
</details>

---

## M4 — Weather + Pest Signals `http://localhost:8004/signals/weather?lat=13.00663&lon=80.244193`


| Method | Endpoint | Description | Input | Output |
|---|---|---|---|---|
| **GET** | `/signals/weather` | Fetch weather signals & pest risks | `lat`, `lon` query params | `SignalBundle` JSON |
| **GET** | `/debug/weather` | Fetch raw diagnostics for debugging | Optional query params | Diagnostics JSON |

<details>
<summary><b>View Example Response JSON (GET <code>/signals/weather</code>)</b></summary>

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
</details>

---

## M5 — Crop Calendar `http://localhost:8005/calendar?state=Tamil+Nadu&crop=blackgram`

| Method | Endpoint | Description | Input | Output |
|---|---|---|---|---|
| **GET** | `/calendar` | Fetch crop growth stage & recommendations | `state`, `crop` query params | `CropStageInfo` JSON |
| **GET** | `/` | Fetch service metadata | None | Service metadata |

<details>
<summary><b>View Example Response JSON (GET <code>/calendar</code>)</b></summary>

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
*Note: MSP and agricultural prices fetched dynamically from Agmarknet API data dashboards.*
</details>

---

## M6 — Context Assembler `http://localhost:8006/context/GRW_00005`


| Method | Endpoint | Description | Input | Output |
|---|---|---|---|---|
| **GET** | `/context/{grower_id}` | Compiles fully unified context for a grower | `grower_id` path param | `FarmerContext` JSON |
| **POST** | `/context/batch` | Compiles context for list of grower IDs | List of grower IDs | Batch context JSON |

<details>
<summary><b>View Example Response JSON (GET <code>/context/GRW_00005</code>)</b></summary>

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
</details>

---

## M7 — Urgency Score `http://localhost:8007/score/GRW_05989` with farmer context gives a score (0-1)


| Method | Endpoint | Description | Input | Output |
|---|---|---|---|---|
| **POST** | `/score` | Get urgency score, fatigue checks & channel preferences | `FarmerContext` JSON body | Urgency Score JSON |
| **POST** | `/explain` | Explain urgency and fatigue decisions | `FarmerContext` JSON body | Explainer JSON |

<details>
<summary><b>View Example Response JSON (POST <code>/score</code>)</b></summary>

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
</details>

---

## M8 — Product Ranker `http://localhost:8008/products/GRW_00012`

| Method | Endpoint | Description | Input | Output |
|---|---|---|---|---|
| **POST** | `/rank` | Fetch ranked list of products for a context | `RankRequest` JSON body | `RankResponse` JSON |
| **GET** | `/products/{grower_id}` | Fetch personalized ranked products by grower ID | `grower_id` path param | Ranked recommendations |

<details>
<summary><b>View Example Response JSON (GET <code>/products/GRW_00012</code>)</b></summary>

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
</details>

---


## M16 — Campaign Orchestrator `http://localhost:8009/predict/GRW_05989` 

| Method | Endpoint | Description | Input | Output |
|---|---|---|---|---|
| **POST** | `/predict` | Predict campaign engagement & fatigue risks | `FarmerContext` body | Campaign Strategy JSON |
| **GET** | `/predict/{grower_id}` | Fetch personalized strategy by grower ID | `grower_id` path param | Strategy JSON |
| **POST** | `/explain` | Explain creative scheduling reasoning | Campaign prediction body | Explainer JSON |

<details>
<summary><b>View Example Response JSON (GET <code>/predict/GRW_05989</code>)</b></summary>

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
</details>

---

## vii. M8 Product Ranker — Performance Evaluation

The evaluation of the Product Ranker module was performed using historical purchase transaction data and agronomic domain rule compliance checks:

- **Historical POS Transactions:** 235,042
- **Registered Growers:** 6,000
- **Products in Catalog:** 12
- **Valid Evaluation Queries:** 37,540
- **Unique Districts Evaluated:** 33
- **Unique Products Purchased:** 12
- **Completed Test Evaluations:** 2,000 queries

### Domain Rule Coherence
- **Rule Verification Examples:**
  -  `wheat + rust` → matches/recommends **Score 250 EC**
  -  `wheat + weeds` → matches/recommends **Topik 15 WP**
  -  `potato + blight` → matches/recommends **Kavach 75 WP**
  -  `chickpea + aphid` → matches/recommends **Actara 25 WG**
  -  `mustard + fungal` → matches/recommends **Score 250 EC**

### Recommendation Performance Metrics
- **Exact Hit Rate @2:** `0.228` (compared to random baseline of `0.173` — **1.3× lift**)
- **Agronomic Hit Rate @2:** `0.647` (compared to random baseline of `0.349` — **1.9× lift**)
- **MoA-aware Hit Rate @2:** `0.466`
- **Functional Recall @2:** `0.831`
- **Exact Hit Rate @5:** `0.664`
- **Agronomic Hit Rate @5:** `0.861`
- **Mean Reciprocal Rank (MRR):** `0.279`
- **Catalog Coverage:** `100%` (proves the engine doesn't suffer from recommendation biases)
- **MoA Diversity Index:** `0.92` (proves that chemical resistance rotation mechanics are successfully integrated)

---
