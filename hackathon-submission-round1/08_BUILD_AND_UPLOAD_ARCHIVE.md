# Build and upload submission archive

Organizers want: **one archive file**, name = **exact registered team name**, shared via link in the submission form.

---

## Step 1 — Confirm team name

From registration email/portal:

```
Team name: [FILL IN EXACTLY]
```

Archive filename:

```
[FILL IN EXACTLY].zip
```

Example: `KrishiMitra_IITM.zip` — **must match**, including spaces/capitals.

---

## Step 2 — Prepare folder contents

Create a **staging folder** (not the whole repo):

```bash
cd ~/Desktop/syngenta/KrishiMitra_syngenta
mkdir -p /tmp/YOUR_TEAM_NAME
```

Copy these (after filling `[FILL IN]` sections):

```bash
TEAM="YOUR_TEAM_NAME"   # change this
STAGE="/tmp/$TEAM"

cp hackathon-submission-round1/01_README_FOR_SUBMISSION.md  "$STAGE/README.md"
cp hackathon-submission-round1/02_TEAM_MEMBERS.md         "$STAGE/TEAM_MEMBERS.md"
cp hackathon-submission-round1/04_SETUP_AND_RUN.md         "$STAGE/SETUP_AND_RUN.md"
cp hackathon-submission-round1/07_API_AND_ENVIRONMENT.md   "$STAGE/API_AND_ENVIRONMENT.md"

# After you export slides:
cp ~/path/to/SOLUTION.pdf "$STAGE/SOLUTION.pdf"

# Video link (do not upload 500MB mp4 if form wants link only)
echo "https://youtu.be/XXXX" > "$STAGE/DEMO_VIDEO_LINK.txt"

# Optional: example farmer context for judges
cp twilio-voice-agent/config/farmer_mayur.example.json "$STAGE/demo_farmer_mayur.json"
```

**Do NOT include:**

- `.venv/`
- `master.db` (optional — small file OK if you want)
- `.env` (secrets)
- `node_modules/`, logs, ngrok cache

**Source code:** link in README only (GitHub).

---

## Step 3 — Create zip

```bash
cd /tmp
zip -r "${TEAM}.zip" "$TEAM"
ls -lh "${TEAM}.zip"
```

Check size (many forms limit 50–100 MB). If too large, remove PDF images or use link-only video.

---

## Step 4 — Upload and get shareable link

### Google Drive

1. Upload `YOUR_TEAM_NAME.zip`
2. Right-click → Share → **Anyone with the link** (Viewer)
3. Copy link

### Alternative: Dropbox / OneDrive / GitHub Release

Same pattern — **view/download** access for judges without login if possible.

---

## Step 5 — Submission form

Paste:

| Field | Value |
|-------|--------|
| Team name | [exact] |
| Archive link | [Drive/Dropbox URL] |
| Repository | [GitHub URL] |
| Video | [YouTube/Drive URL] |
| Live app | `N/A` or ngrok/Cloud URL |

---

## Final checklist before submit

- [ ] Zip name == registered team name  
- [ ] README has all five sections (i–v)  
- [ ] Every team member in `TEAM_MEMBERS.md` and **demo video**  
- [ ] `SOLUTION.pdf` or slides attached  
- [ ] `SETUP_AND_RUN.md` tested on clean machine or teammate laptop  
- [ ] GitHub repo public and link works  
- [ ] No API keys in any uploaded file  
- [ ] Submitted before deadline (IST)

---

## Quick command (after editing files in repo)

```bash
cd /home/rajnish/Desktop/syngenta/KrishiMitra_syngenta
# Edit TEAM variable first!
bash hackathon-submission-round1/pack_submission.sh
```

(See `pack_submission.sh` — run after setting your team name inside the script.)
