# Future plans

Short backlog for improvements that are **not** in this voice repo today but are relevant to the broader product (e.g. identity / face verification that is working “somewhat nice” and should get better over time).

## Face match / KYC verification

**Goal:** Improve match reliability when comparing a reference photo to live or recorded video (same person, “no match” false negatives, bad frames).

| Priority | Item | Notes |
|----------|------|--------|
| High | **Consistent preprocessing** | Same face detector + alignment (e.g. 5-point or 106-point landmarks) and crop size for **both** reference image and video frames before embedding. |
| High | **Single embedding model** | One model family end-to-end (e.g. same ArcFace / InsightFace variant); avoid mixing providers or versions between enrollment and verify. |
| High | **Multi-frame fusion from video** | Extract embeddings from several good frames; use **median** or **trimmed mean** of similarities (or average embeddings then L2-normalize) to reduce one bad frame dominating. |
| Medium | **Frame quality gate (FIQA)** | Skip or down-weight dark, blurry, tiny, or side-profile frames; prefer frontal, well-lit, in-focus crops. |
| Medium | **Two-threshold policy** | e.g. `match` / `uncertain` / `no match` with optional human review on uncertain band instead of binary pass-fail. |
| Medium | **Calibration** | Collect labeled pairs (same / different) on real devices; tune thresholds per demographic/lighting if metrics show skew (careful with fairness). |
| Lower | **Liveness / anti-spoof** | If required for compliance: depth, challenge-response, or dedicated liveness model (separate from pure face match). |
| Lower | **Script / phrase alignment** | If product requires “say this phrase”: combine transcript check with face match for that segment only. |

**Implementation note:** Face matching is **not** implemented in this repository (voice + Twilio + Gemini). When built, prefer a **small dedicated service or module** (clear API: enroll, verify, scores) so the web KYC UI and this stack stay decoupled.

## Voice stack (this repo)

Ongoing ideas already partially addressed elsewhere: persona tuning, TTS-friendly text cleaning, retries on transient model errors, `VOICE_ENGINE` / Live API configuration, optional call recording flags, tunnel env for local dev.

---

*Add dated entries below when items ship or scope changes.*
