# Source code repository — guidance

You already have a GitHub repo. Use this checklist before submission.

---

## Before you share the link

- [ ] Repo is **public** OR organizers have been granted access (confirm hackathon rules).
- [ ] **No secrets** in git history — `.env` is in `.gitignore`; rotate keys if anything was committed by mistake.
- [ ] **README.md** at repo root is readable (your main technical README exists).
- [ ] **`.env.example`** is present (judges know what keys are needed).
- [ ] Large folders **not** required for judges: `.venv/`, `master.db`, `whatsapp_apps/web/sessions/`, `twilio-voice-agent/logs/`.

---

## What to paste in submission form

```
Repository: https://github.com/[ORG]/[REPO]
Branch: main
Commit (optional, for reproducibility): [git rev-parse --short HEAD]
```

---

## If repo is monorepo (syngenta folder)

Judges should clone and enter the app folder:

```bash
git clone [URL]
cd KrishiMitra_syngenta    # or path shown on GitHub
```

If `twilio-voice-agent` is a **nested git repo**, mention in README:

> Voice agent may be a submodule or separate folder; see `twilio-voice-agent/README_KRISHIMITRA.md`.

---

## Optional: GitHub Release for submission archive

Instead of only Google Drive, you can attach the zip to a **GitHub Release**:

1. Tag: `submission-round1-2026-05-20`
2. Upload: `YOUR_TEAM_NAME.zip`
3. Put release URL in submission form as backup to Drive link

---

## README link in archive

Copy filled `01_README_FOR_SUBMISSION.md` → rename to **`README.md`** inside the zip (organizers open this first).
