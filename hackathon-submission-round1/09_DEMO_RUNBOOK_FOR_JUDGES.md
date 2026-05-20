# Demo runbook — 3-minute live demo (judges or video)

**Story:** Outreach to **Mayur**, cotton farmer in **Boriavi, Anand, Gujarat**, in **Gujarati**, with ranked products and SMS/voice.

---

## Before you start (30 sec)

```bash
cd KrishiMitra_syngenta
source .venv/bin/activate
./run_all.sh
```

Verify:

```bash
curl -s http://127.0.0.1:8008/health | grep catalog_size
curl -s http://127.0.0.1:8001/farmers | grep GJ-014
```

---

## Beat 1 — “We know the farmer” (45 sec)

```bash
curl -s http://127.0.0.1:8006/context/GJ-014  | python -m json.tool | head -45
```

**Say:**  
“This is Mayur in Anand, Gujarat. He grows cotton, prefers Gujarati, has a smartphone on 4G. We merged his profile with weather signals and crop stage into one FarmerContext.”

---

## Beat 2 — “We rank the right product” (45 sec)

```bash
curl -s http://127.0.0.1:8008/products/GJ-014  | python -m json.tool | head -55
```

**Say:**  
“M8 scores Syngenta catalog products for his crop and risk. Each recommendation includes human-readable reasons—not a black box.”

---

## Beat 3 — “We send in his language” (60 sec)

**SMS preview:**

```bash
cd twilio-voice-agent
python scripts/send_farmer_sms.py --json config/farmer_mayur.example.json --preview
```

**Say:**  
“Same JSON drives SMS, WhatsApp, and voice. Scripts are in Gujarati with cotton and whitefly context.”

**Optional live SMS** (Twilio configured):

```bash
python scripts/send_farmer_sms.py --json config/farmer_mayur.example.json
```

**Optional voice** (second terminal, `./start.sh` running):

```bash
python scripts/krishimitra_call.py --json config/farmer_mayur.example.json
```

---

## Beat 4 — Close (15 sec)

**Say:**  
“KrishiMitra is context-first: assemble → score → rank → reach. Code and setup are in the README. Thank you.”

---

## Backup if network fails

Show files only:

- `twilio-voice-agent/config/farmer_mayur.example.json`
- Terminal screenshot of health + context JSON (prepare beforehand)

---

## Farmer IDs for quick tests

| ID | Name | Region | Crop |
|----|------|--------|------|
| GJ-014 | Mayur | Gujarat | cotton |
| GJ-014 | Grower | UP | wheat |
| BR-001 | Rajnish | Bihar | rice |
