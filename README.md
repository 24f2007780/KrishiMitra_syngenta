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
  ],
```

## M8 — Product Ranker

```json
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
