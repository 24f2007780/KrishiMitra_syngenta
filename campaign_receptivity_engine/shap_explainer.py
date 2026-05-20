"""
Campaign Receptivity Engine — SHAP HTML Explainability
Syngenta IITM Hackathon 2026

Generates detailed standalone HTML pages explaining:
  - Why this farmer was classified into this segment
  - What drives their receptivity score (SHAP waterfall)
  - Why specific formats were recommended
  - Fatigue risk decomposition
  - Creative strategy rationale

Uses TreeExplainer when XGBoost model is available,
analytical decomposition otherwise.
"""

import logging
import math
import html as html_lib
from typing import List, Tuple, Optional
from datetime import date

import numpy as np

from shared.models import (
    ReceptivityRequest, FarmerSegment, CampaignFormat,
)
from .predictor import predict_receptivity, _load_model, _classify_segment, _build_features

logger = logging.getLogger(__name__)

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False


FEATURE_NAMES = [
    "Behavioral Segment",
    "Device Type",
    "Month of Year",
    "Day of Week",
    "Historical Open Rate",
    "Historical Click Rate",
    "Messages in Last 30 Days",
    "Farm Size (acres)",
    "Grower Age",
    "Product Scanned",
    "Offline Campaign Attended",
    "District Engagement Rate",
    "Crop Engagement Rate",
]


def _get_shap_values(request: ReceptivityRequest, payload: dict) -> Optional[List[Tuple[str, float, float]]]:
    """
    Compute SHAP values using TreeExplainer on the XGBoost model.
    Returns list of (feature_name, feature_value, shap_value).
    """
    if not SHAP_AVAILABLE or payload is None or payload.get("pipeline") is None:
        return None

    try:
        segment, _ = _classify_segment(request, payload)
        fv = _build_features(request, segment, payload)

        pipeline = payload["pipeline"]
        scaler = pipeline.named_steps["scaler"]
        calibrated_clf = pipeline.named_steps["model"]

        fv_scaled = scaler.transform(fv)

        # Get base XGBoost model from calibrated wrapper
        base_model = calibrated_clf.calibrated_classifiers_[0].estimator

        explainer = shap.TreeExplainer(base_model)
        shap_values = explainer.shap_values(fv_scaled)

        if isinstance(shap_values, list):
            sv = shap_values[1][0] if len(shap_values) > 1 else shap_values[0][0]
        else:
            sv = shap_values[0]

        contributions = []
        for i, name in enumerate(FEATURE_NAMES):
            feat_val = float(fv[0, i])
            shap_val = float(sv[i])
            contributions.append((name, feat_val, shap_val))

        return contributions
    except Exception as exc:
        logger.warning("SHAP TreeExplainer failed: %s", exc)
        return None


def _analytical_shap(request: ReceptivityRequest, payload: dict) -> List[Tuple[str, float, float]]:
    """
    Analytical feature contribution when SHAP library unavailable.
    Uses feature importance × feature value as proxy.
    """
    segment, _ = _classify_segment(request, payload or {})
    fv = _build_features(request, segment, payload) if payload else np.zeros((1, 13))

    # Approximate importances (from typical XGBoost training)
    importances = [0.15, 0.08, 0.06, 0.04, 0.18, 0.20, 0.07, 0.05, 0.04, 0.06, 0.04, 0.02, 0.01]

    contributions = []
    for i, name in enumerate(FEATURE_NAMES):
        val = float(fv[0, i]) if fv.shape[1] > i else 0.0
        # Normalize contribution
        contrib = val * importances[i] if i < len(importances) else 0.0
        contributions.append((name, val, contrib))

    return contributions


def generate_shap_html(request: ReceptivityRequest) -> str:
    """
    Main entry point. Generates a comprehensive SHAP explanation HTML page.
    """
    payload = _load_model()
    result = predict_receptivity(request)

    # Get SHAP values
    shap_contributions = _get_shap_values(request, payload)
    if shap_contributions is None:
        shap_contributions = _analytical_shap(request, payload)

    # Sort by absolute contribution
    shap_sorted = sorted(shap_contributions, key=lambda x: abs(x[2]), reverse=True)

    return _render_full_html(request, result, shap_sorted, payload)


def _render_full_html(request, result, shap_contributions, payload) -> str:
    """Render the complete detailed SHAP explanation page."""

    # ── Waterfall bars ──
    significant = [(n, v, s) for n, v, s in shap_contributions if abs(s) > 0.001][:10]
    max_abs = max(abs(s[2]) for s in significant) if significant else 1.0
    bar_scale = 260.0 / max_abs if max_abs > 0 else 1.0

    waterfall_rows = ""
    for name, feat_val, shap_val in significant:
        bar_width = max(abs(shap_val) * bar_scale, 3)
        is_pos = shap_val >= 0
        color = "#e74c3c" if is_pos else "#3498db"
        direction = "+" if is_pos else "−"
        label = f"{direction}{abs(shap_val):.4f}"

        if feat_val == int(feat_val) and abs(feat_val) < 100:
            val_display = f"{int(feat_val)}"
        else:
            val_display = f"{feat_val:.3f}"

        waterfall_rows += f"""
        <tr class="wf-row">
            <td class="wf-name">{html_lib.escape(name)}</td>
            <td class="wf-val">{val_display}</td>
            <td class="wf-bar">
                <div class="bar-wrap">
                    <div class="bar" style="width:{bar_width:.0f}px;background:{color};"></div>
                    <span class="bar-lbl" style="color:{color};">{label}</span>
                </div>
            </td>
        </tr>"""

    # ── Segment explanation ──
    seg_explanations = {
        FarmerSegment.digital_active: ("High digital engagement — opens and clicks regularly. Best reached via rich media WhatsApp.", "#27ae60"),
        FarmerSegment.digital_passive: ("Opens messages but rarely clicks. Needs stronger hooks and clearer CTAs.", "#f39c12"),
        FarmerSegment.offline_only: ("Does not engage with digital channels. Requires voice, SMS, or field visits.", "#e74c3c"),
        FarmerSegment.new_farmer: ("No engagement history available. Using population priors for prediction.", "#3498db"),
    }
    seg_desc, seg_color = seg_explanations.get(result.segment, ("Unknown segment", "#7f8c8d"))

    # ── Format bars ──
    format_rows = ""
    for fmt in result.recommended_formats:
        pct = fmt.predicted_engagement * 100
        bar_w = pct * 12  # scale for visual
        format_rows += f"""
        <div class="fmt-row">
            <div class="fmt-name">{fmt.format.value.replace('_', ' ').title()}</div>
            <div class="fmt-bar-wrap">
                <div class="fmt-bar" style="width:{bar_w:.0f}px;"></div>
                <span class="fmt-pct">{pct:.1f}%</span>
            </div>
            <div class="fmt-reason">{html_lib.escape(fmt.reasoning)}</div>
        </div>"""

    # ── Fatigue gauge ──
    fatigue_pct = result.fatigue_risk * 100
    fatigue_color = "#e74c3c" if result.fatigue_risk > 0.6 else "#f39c12" if result.fatigue_risk > 0.3 else "#27ae60"
    fatigue_label = "HIGH — Back off" if result.fatigue_risk > 0.6 else "MODERATE" if result.fatigue_risk > 0.3 else "LOW — Safe to message"

    # ── Creative suggestions ──
    suggestions_html = ""
    for s in result.creative_suggestions:
        suggestions_html += f'<li>{html_lib.escape(s)}</li>'

    # ── Timing ──
    timing_html = f"""
    <div class="timing-card">
        <div class="timing-item"><span class="timing-icon">📅</span> <strong>Best Days:</strong> {result.best_day_of_week or 'N/A'}</div>
        <div class="timing-item"><span class="timing-icon">⏰</span> <strong>Best Time:</strong> {result.best_time_window or 'N/A'}</div>
    </div>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Campaign Receptivity — SHAP Explanation</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:'Segoe UI',-apple-system,sans-serif;background:linear-gradient(135deg,#f0f4f8 0%,#d9e2ec 100%);min-height:100vh;padding:1.5rem;color:#2c3e50;}}
.container{{max-width:960px;margin:0 auto;background:#fff;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,0.08);overflow:hidden;}}
.header{{background:linear-gradient(135deg,#2c3e50 0%,#3498db 100%);color:#fff;padding:2rem 2.5rem;}}
.header h1{{font-size:1.5rem;font-weight:600;}}
.header .sub{{opacity:0.85;font-size:0.85rem;margin-top:0.3rem;}}
.scores-row{{display:flex;gap:1rem;padding:1.5rem 2rem;background:#f8fafc;border-bottom:1px solid #e2e8f0;flex-wrap:wrap;}}
.score-card{{flex:1;min-width:130px;text-align:center;padding:1rem;border-radius:10px;background:#fff;box-shadow:0 2px 6px rgba(0,0,0,0.04);}}
.score-card .lbl{{font-size:0.68rem;text-transform:uppercase;letter-spacing:0.5px;color:#7f8c8d;margin-bottom:0.3rem;}}
.score-card .val{{font-size:1.7rem;font-weight:700;}}
.score-high .val{{color:#e74c3c;}}
.score-mid .val{{color:#f39c12;}}
.score-low .val{{color:#27ae60;}}
.section{{padding:1.5rem 2rem;border-bottom:1px solid #f0f0f0;}}
.section:last-child{{border-bottom:none;}}
.section h3{{font-size:1rem;color:#2c3e50;margin-bottom:1rem;padding-bottom:0.4rem;border-bottom:2px solid #ebf5fb;}}
.seg-badge{{display:inline-block;padding:0.4rem 1rem;border-radius:20px;font-size:0.8rem;font-weight:600;color:#fff;background:{seg_color};}}
.seg-desc{{font-size:0.85rem;color:#555;margin-top:0.5rem;}}
table.wf{{width:100%;border-collapse:collapse;}}
.wf-row td{{padding:0.5rem 0.4rem;border-bottom:1px solid #f5f5f5;vertical-align:middle;}}
.wf-row:hover td{{background:#fafbfc;}}
.wf-name{{font-size:0.82rem;font-weight:500;color:#34495e;width:200px;}}
.wf-val{{font-size:0.78rem;color:#7f8c8d;width:60px;text-align:right;font-family:monospace;}}
.wf-bar{{width:100%;}}
.bar-wrap{{display:flex;align-items:center;gap:8px;}}
.bar{{height:20px;border-radius:4px;opacity:0.85;}}
.bar-lbl{{font-size:0.72rem;font-weight:600;font-family:monospace;white-space:nowrap;}}
.legend{{display:flex;gap:1.5rem;margin-top:1rem;padding:0.6rem 1rem;background:#f8f9fa;border-radius:6px;font-size:0.78rem;}}
.legend-item{{display:flex;align-items:center;gap:5px;}}
.legend-dot{{width:12px;height:12px;border-radius:3px;}}
.fmt-row{{display:flex;align-items:center;gap:1rem;padding:0.6rem 0;border-bottom:1px solid #f5f5f5;}}
.fmt-name{{width:140px;font-size:0.82rem;font-weight:500;}}
.fmt-bar-wrap{{display:flex;align-items:center;gap:6px;width:200px;}}
.fmt-bar{{height:18px;background:linear-gradient(90deg,#3498db,#2980b9);border-radius:4px;}}
.fmt-pct{{font-size:0.75rem;font-weight:600;color:#2980b9;}}
.fmt-reason{{flex:1;font-size:0.78rem;color:#7f8c8d;}}
.fatigue-gauge{{display:flex;align-items:center;gap:1rem;padding:1rem;background:#f8f9fa;border-radius:8px;margin:0.5rem 0;}}
.fatigue-bar-bg{{flex:1;height:12px;background:#ecf0f1;border-radius:6px;overflow:hidden;}}
.fatigue-bar-fill{{height:100%;border-radius:6px;transition:width 0.3s;background:{fatigue_color};}}
.fatigue-label{{font-size:0.8rem;font-weight:600;color:{fatigue_color};min-width:120px;}}
.timing-card{{display:flex;gap:2rem;padding:1rem;background:#f0faf0;border-radius:8px;margin:0.5rem 0;}}
.timing-item{{font-size:0.85rem;}}
.timing-icon{{font-size:1.1rem;}}
.suggestions{{list-style:none;padding:0;}}
.suggestions li{{padding:0.5rem 0;font-size:0.85rem;border-bottom:1px solid #f8f8f8;}}
.suggestions li::before{{content:"💡 ";}}
.footer{{padding:1rem 2rem;background:#f8f9fa;border-top:1px solid #ecf0f1;font-size:0.72rem;color:#95a5a6;display:flex;justify-content:space-between;}}
.detail-box{{background:#fafbfc;border:1px solid #e8ecf0;border-radius:8px;padding:1rem;margin:0.8rem 0;font-size:0.82rem;}}
.detail-box h5{{font-size:0.78rem;color:#2980b9;margin-bottom:0.4rem;text-transform:uppercase;letter-spacing:0.5px;}}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>📊 Campaign Receptivity — SHAP Explanation</h1>
        <div class="sub">Grower: {html_lib.escape(request.grower_id or 'Anonymous')} &nbsp;|&nbsp; Crop: {request.crop.value} &nbsp;|&nbsp; {result.model_version}</div>
    </div>

    <div class="scores-row">
        <div class="score-card {'score-high' if result.receptivity_score >= 0.7 else 'score-mid' if result.receptivity_score >= 0.4 else 'score-low'}">
            <div class="lbl">Receptivity</div>
            <div class="val">{result.receptivity_score:.2f}</div>
        </div>
        <div class="score-card">
            <div class="lbl">Segment</div>
            <div class="val" style="font-size:0.9rem;">{result.segment.value.replace('_',' ').title()}</div>
        </div>
        <div class="score-card {'score-high' if result.fatigue_risk >= 0.6 else 'score-mid' if result.fatigue_risk >= 0.3 else 'score-low'}">
            <div class="lbl">Fatigue Risk</div>
            <div class="val">{result.fatigue_risk:.2f}</div>
        </div>
        <div class="score-card">
            <div class="lbl">Confidence</div>
            <div class="val">{result.segment_confidence:.2f}</div>
        </div>
    </div>

    <div class="section">
        <h3>Farmer Segment Classification</h3>
        <span class="seg-badge">{result.segment.value.replace('_',' ').upper()}</span>
        <p class="seg-desc">{seg_desc}</p>
        <div class="detail-box">
            <h5>How was this segment determined?</h5>
            <p style="margin:0;">{'Based on historical click rate > 8%' if result.segment == FarmerSegment.digital_active else 'Based on historical open rate > 30% but low click rate' if result.segment == FarmerSegment.digital_passive else 'Device type is keypad — cannot receive WhatsApp' if result.segment == FarmerSegment.offline_only else 'No engagement history available — using profile signals and population priors'}</p>
        </div>
    </div>

    <div class="section">
        <h3>SHAP Feature Contributions (What Drives Receptivity)</h3>
        <table class="wf">
            <thead><tr style="font-size:0.7rem;color:#95a5a6;text-transform:uppercase;letter-spacing:0.5px;">
                <td style="padding-bottom:0.5rem;">Feature</td>
                <td style="padding-bottom:0.5rem;text-align:right;">Value</td>
                <td style="padding-bottom:0.5rem;">SHAP Contribution</td>
            </tr></thead>
            <tbody>{waterfall_rows}</tbody>
        </table>
        <div class="legend">
            <div class="legend-item"><div class="legend-dot" style="background:#e74c3c;"></div><span>Increases receptivity</span></div>
            <div class="legend-item"><div class="legend-dot" style="background:#3498db;"></div><span>Decreases receptivity</span></div>
        </div>
        <div class="detail-box">
            <h5>Interpretation</h5>
            <p style="margin:0;">Each bar shows how much a feature pushes the receptivity prediction up (red) or down (blue) from the baseline. Longer bars = stronger influence on the final score.</p>
        </div>
    </div>

    <div class="section">
        <h3>Recommended Creative Formats</h3>
        {format_rows}
        <div class="detail-box">
            <h5>Why these formats?</h5>
            <p style="margin:0;">Format recommendations are based on segment-level engagement patterns from historical campaign data. The {result.segment.value.replace('_',' ')} segment historically responds best to the formats shown above. {'WhatsApp formats excluded because device is keypad.' if request.device_type.value == 'keypad' else ''}</p>
        </div>
    </div>

    <div class="section">
        <h3>Fatigue Risk Assessment</h3>
        <div class="fatigue-gauge">
            <div class="fatigue-bar-bg"><div class="fatigue-bar-fill" style="width:{fatigue_pct:.0f}%;"></div></div>
            <div class="fatigue-label">{fatigue_label}</div>
        </div>
        <div class="detail-box">
            <h5>Fatigue calculation</h5>
            <p style="margin:0;">Messages received in last 30 days: <strong>{request.messages_received_last_30d if request.messages_received_last_30d is not None else 'Unknown'}</strong>. Segment fatigue threshold: {'6 messages' if result.segment == FarmerSegment.digital_active else '3 messages' if result.segment == FarmerSegment.digital_passive else '1 message' if result.segment == FarmerSegment.offline_only else '2 messages'}. {'Current volume exceeds threshold — reduce frequency or switch to high-value content only.' if result.fatigue_risk > 0.6 else 'Within acceptable range.' if result.fatigue_risk < 0.4 else 'Approaching threshold — monitor closely.'}</p>
        </div>
    </div>

    <div class="section">
        <h3>Optimal Timing</h3>
        {timing_html}
        <div class="detail-box">
            <h5>Why this timing?</h5>
            <p style="margin:0;">Timing recommendations are derived from segment-level engagement patterns. The {result.segment.value.replace('_',' ')} segment shows highest open rates during {result.best_day_of_week or 'midweek'} in the {result.best_time_window or 'morning'} window. Agricultural workers are typically available before field work begins.</p>
        </div>
    </div>

    <div class="section">
        <h3>Creative Strategy Suggestions</h3>
        <ul class="suggestions">{suggestions_html}</ul>
    </div>

    <div class="footer">
        <span>Syngenta IITM Hackathon 2026 — Campaign Receptivity Engine</span>
        <span>{'SHAP TreeExplainer' if SHAP_AVAILABLE and payload and payload.get('pipeline') else 'Analytical Decomposition'}</span>
    </div>
</div>
</body>
</html>"""
    return html
