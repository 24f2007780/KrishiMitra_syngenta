# Demo video guide (all team members required)

**Target length:** 4–6 minutes (max 8 if rules allow)  
**Format:** MP4, 1080p, clear audio  
**Upload:** YouTube (unlisted) or Google Drive → put link in `DEMO_VIDEO_LINK.txt` and README

---

## Pre-recording checklist

- [ ] `./run_all.sh` running; `curl http://127.0.0.1:8006/health` OK  
- [ ] Terminal font size **18+** (readable on phone)  
- [ ] Close unrelated notifications  
- [ ] Twilio/Gemini keys in `.env` if showing **live** SMS/call (or say “simulated” for API-only)  
- [ ] Each member **on camera** at least once (organizer requirement)  
- [ ] Test screen recorder: OBS / Zoom record / Loom / phone

---

## Suggested script (5 minutes)

| Time | Who | What to show / say |
|------|-----|-------------------|
| 0:00–0:30 | **Member 1** (on camera) | “We are Team [NAME]. KrishiMitra helps Syngenta reach the right farmer at the right moment—in their language.” |
| 0:30–1:00 | Member 1 | Problem: generic SMS vs our approach (who / why now / what / how) |
| 1:00–1:30 | **Member 2** (on camera) | Screen: `./run_all.sh`, health curls 8001/8006/8008 |
| 1:30–2:30 | Member 2 | `curl .../farmers` → pick **Mayur GJ-014** → `curl .../context/GJ-014` — point to Gujarat, cotton, Gujarati |
| 2:30–3:15 | Member 2 | `curl .../products/GJ-014` — explain top product + match_reasons |
| 3:15–4:15 | **Member 3** (on camera) | SMS: `send_farmer_sms.py --preview` then send OR voice: `krishimitra_call.py` — phone rings, Gujarati intro |
| 4:15–4:45 | Member 3 | Optional: WhatsApp message screenshot |
| 4:45–5:00 | **All on camera** | “Repo link in README. Thank you.” |

---

## B-roll shots to capture

1. Terminal — green health JSON  
2. Pretty-printed `FarmerContext` for GJ-014  
3. Rank response with `top_products`  
4. Phone receiving SMS or incoming call  
5. Slide 3 architecture (optional overlay)

---

## If live call/SMS fails during recording

**Do not panic.** Record:

1. `--preview` SMS output (shows Gujarati text)  
2. `krishimitra_call.py` returning `200 {"success":true,"call_sid":"..."}`  
3. Say: “Trial Twilio requires verified numbers; pipeline is integrated.”

---

## Audio tips

- Use external mic or quiet room  
- One person narrates screen; others introduce themselves first  
- Add **subtitles** (YouTube auto-caption + fix names)

---

## File to include in zip

Create **`DEMO_VIDEO_LINK.txt`** with one line:

```
https://youtu.be/XXXXXXXX   # or Google Drive view link
```

---

## Naming

`TeamName_Demo_Round1.mp4` — keep a copy inside the zip only if size &lt; 100 MB; otherwise link-only is fine per many hackathons.
