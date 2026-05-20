"""
M7 Intelligence Engine — SHAP HTML Explainability
Syngenta IITM Hackathon 2026

Generates standalone HTML pages explaining the 3-layer scoring decision:
  Layer 1: Agronomic urgency (analytical SHAP — exact marginal contributions)
  Layer 2: Behavioral engagement (TreeExplainer if available, else priors)
  Layer 3: Delivery intelligence (fusion + channel recommendation)
"""

import math
import logging
import html as html_lib
from typing import List, Tuple
from datetime import date

import numpy as np

from shared.models import FarmerContext
from .scorer import compute_urgency, compute_recency_penalty, _clip

logger = logging.getLogger(__name__)


def generate_shap_html(ctx: FarmerContext) -> str:
    """
    Main entry point. Scores the farmer and renders a full HTML explanation.
    """
    result = compute_urgency(ctx)

    # Analytical SHAP for Layer 1 (exact contributions from formula)
    recency_penalty = compute_recency_penalty(ctx.last_message_date, ctx.scoring_date)
    urgency_contributions = [
        ("Pest Outbreak Risk", ctx.pest_risk, 0.40 * ctx.pest_risk),
        ("Weather Anomaly", ctx.weather_anomaly, 0.30 * ctx.weather_anomaly),
        ("Crop Stage Vulnerability", ctx.crop_vulnerability, 0.20 * ctx.crop_vulnerability),
        ("Communication Window", 1.0 - recency_penalty, 0.10 * (1.0 - recency_penalty)),
    ]

    # Engagement factors from result
    eng_factors = result.engagement_components.get("top_factors", [])
    eng_score = result.engagement_score
    is_cold_start = result.engagement_components.get("cold_start", False)

    return _render_html(
        grower_id=ctx.grower_id,
        urgency_score=result.urgency_score,
        engagement_score=result.engagement_score,
        intervention_priority=result.intervention_priority,
        channel=result.recommended_channel.value,
        suppress=result.suppress,
        suppress_reason=result.suppress_reason,
        urgency_contributions=urgency_contributions,
        engagement_factors=eng_factors,
        is_cold_start=is_cold_start,
        top_factors=result.top_factors,
        model_version=result.model_version,
    )


def _render_html(
    grower_id: str,
    urgency_score: float,
    engagement_score: float,
    intervention_priority: float,
    channel: str,
    suppress: bool,
    suppress_reason: str,
    urgency_contributions: List[Tuple[str, float, float]],
    engagement_factors: List[str],
    is_cold_start: bool,
    top_factors: List[str],
    model_version: str,
) -> str:
    """Renders the full 3-layer explanation as standalone HTML."""

    # Urgency waterfall bars
    max_contrib = max(c[2] for c in urgency_contributions) if urgency_contributions else 1.0
    bar_scale = 250.0 / max_contrib if max_contrib > 0 else 1.0

    urgency_rows = ""
    for name, feat_val, contrib in urgency_contributions:
        bar_width = max(contrib * bar_scale, 2)
        color = "#e74c3c" if contrib > 0.05 else "#95a5a6"
        val_display = f"{feat_val:.2f}"
        urgency_rows += f"""
        <tr>
            <td class="feat-name">{html_lib.escape(name)}</td>
            <td class="feat-val">{val_display}</td>
            <td class="bar-cell">
                <div class="bar-container">
                    <div class="bar" style="width:{bar_width:.0f}px; background:{color};"></div>
                    <span class="bar-label" style="color:{color};">+{contrib:.3f}</span>
                </div>
            </td>
        </tr>"""

    # Engagement factors list
    eng_items = ""
    for f in engagement_factors:
        eng_items += f'<li>{html_lib.escape(f)}</li>'
    cold_start_badge = '<span class="badge badge-cold">COLD START — Population Priors</span>' if is_cold_start else '<span class="badge badge-ml">ML Model</span>'

    # Channel display
    channel_icons = {
        "whatsapp": "📱 WhatsApp",
        "voice_call": "📞 Voice Call",
        "sms": "💬 SMS",
        "field_visit": "🚜 Field Visit",
        "suppress": "⏸️ Suppressed",
    }
    channel_display = channel_icons.get(channel, channel)

    # Suppress badge
    if suppress:
        suppress_html = f'<div class="suppress-alert">⚠️ <strong>SUPPRESSED</strong> — {html_lib.escape(suppress_reason or "")}</div>'
    else:
        suppress_html = ""

    # Score colors
    def score_class(s):
        if s >= 0.7:
            return "score-high"
        elif s >= 0.4:
            return "score-mid"
        return "score-low"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>M7 Explanation — {html_lib.escape(grower_id)}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    font-family: 'Segoe UI', -apple-system, sans-serif;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    min-height: 100vh; padding: 1.5rem; color: #2c3e50;
}}
.container {{ max-width:920px; margin:0 auto; background:#fff; border-radius:16px; box-shadow:0 20px 60px rgba(0,0,0,0.1); overflow:hidden; }}
.header {{ background:linear-gradient(135deg,#1a5e1f,#2d8f33); color:#fff; padding:1.5rem 2rem; }}
.header h1 {{ font-size:1.4rem; font-weight:600; }}
.header .sub {{ opacity:0.85; font-size:0.85rem; margin-top:0.2rem; }}
.scores-row {{ display:flex; gap:1rem; padding:1.5rem 2rem; background:#f8faf8; border-bottom:1px solid #e8ece8; flex-wrap:wrap; }}
.score-card {{ flex:1; min-width:140px; text-align:center; padding:1rem; border-radius:12px; background:#fff; box-shadow:0 2px 8px rgba(0,0,0,0.06); }}
.score-card .label {{ font-size:0.7rem; text-transform:uppercase; letter-spacing:0.5px; color:#7f8c8d; margin-bottom:0.4rem; }}
.score-card .value {{ font-size:1.8rem; font-weight:700; }}
.score-high .value {{ color:#c0392b; }}
.score-mid .value {{ color:#e67e22; }}
.score-low .value {{ color:#27ae60; }}
.channel-card {{ flex:1; min-width:140px; text-align:center; padding:1rem; border-radius:12px; background:#eaf7ea; }}
.channel-card .label {{ font-size:0.7rem; text-transform:uppercase; letter-spacing:0.5px; color:#7f8c8d; margin-bottom:0.4rem; }}
.channel-card .value {{ font-size:1.1rem; font-weight:600; color:#1a5e1f; }}
.section {{ padding:1.2rem 2rem; }}
.section h3 {{ font-size:0.95rem; color:#2c3e50; margin-bottom:0.8rem; padding-bottom:0.4rem; border-bottom:2px solid #ecf0f1; }}
table {{ width:100%; border-collapse:collapse; }}
tr td {{ padding:0.5rem 0.4rem; border-bottom:1px solid #f0f0f0; vertical-align:middle; }}
.feat-name {{ font-size:0.82rem; font-weight:500; color:#34495e; width:200px; }}
.feat-val {{ font-size:0.78rem; color:#7f8c8d; width:60px; text-align:right; font-family:monospace; }}
.bar-cell {{ width:100%; }}
.bar-container {{ display:flex; align-items:center; gap:8px; }}
.bar {{ height:20px; border-radius:4px; }}
.bar-label {{ font-size:0.72rem; font-weight:600; font-family:monospace; white-space:nowrap; }}
.badge {{ display:inline-block; padding:0.2rem 0.6rem; border-radius:12px; font-size:0.7rem; font-weight:600; text-transform:uppercase; }}
.badge-cold {{ background:#fff3cd; color:#856404; border:1px solid #ffc107; }}
.badge-ml {{ background:#d4edda; color:#155724; border:1px solid #c3e6cb; }}
.eng-list {{ list-style:none; padding:0; }}
.eng-list li {{ padding:0.4rem 0; font-size:0.85rem; border-bottom:1px solid #f8f8f8; }}
.eng-list li::before {{ content:"→ "; color:#2d8f33; font-weight:bold; }}
.suppress-alert {{ background:#fdecea; border:1px solid #f5c6cb; border-radius:8px; padding:0.8rem 1rem; margin:1rem 0; font-size:0.85rem; color:#721c24; }}
.top-factors {{ padding:0.8rem 1rem; background:#f0faf0; border-radius:8px; margin-top:0.8rem; }}
.top-factors h4 {{ font-size:0.8rem; color:#1a5e1f; margin-bottom:0.4rem; }}
.top-factors ul {{ list-style:none; padding:0; }}
.top-factors ul li {{ font-size:0.82rem; padding:0.2rem 0; }}
.top-factors ul li::before {{ content:"✓ "; color:#27ae60; }}
.footer {{ padding:0.8rem 2rem; background:#f8f9fa; border-top:1px solid #ecf0f1; font-size:0.72rem; color:#95a5a6; display:flex; justify-content:space-between; }}
.formula {{ font-family:monospace; font-size:0.78rem; background:#f8f9fa; padding:0.6rem 1rem; border-radius:6px; border-left:3px solid #2d8f33; margin:0.5rem 0; }}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🌾 M7 Intelligence Engine — Scoring Explanation</h1>
        <div class="sub">Grower: {html_lib.escape(grower_id)} &nbsp;|&nbsp; {model_version}</div>
    </div>

    <div class="scores-row">
        <div class="score-card {score_class(urgency_score)}">
            <div class="label">Agronomic Urgency</div>
            <div class="value">{urgency_score:.2f}</div>
        </div>
        <div class="score-card {score_class(engagement_score)}">
            <div class="label">Engagement Likelihood</div>
            <div class="value">{engagement_score:.2f}</div>
        </div>
        <div class="score-card {score_class(intervention_priority)}">
            <div class="label">Priority Score</div>
            <div class="value">{intervention_priority:.2f}</div>
        </div>
        <div class="channel-card">
            <div class="label">Recommended Channel</div>
            <div class="value">{channel_display}</div>
        </div>
    </div>

    {suppress_html}

    <div class="section">
        <h3>Layer 1: Agronomic Urgency (Rule Engine)</h3>
        <div class="formula">
            urgency = 0.40×pest + 0.30×weather + 0.20×vulnerability + 0.10×(1 − recency)
            = <strong>{urgency_score:.2f}</strong>
        </div>
        <table>
            <thead><tr style="font-size:0.7rem;color:#95a5a6;text-transform:uppercase;">
                <td>Factor</td><td style="text-align:right">Value</td><td>Contribution</td>
            </tr></thead>
            <tbody>{urgency_rows}</tbody>
        </table>
    </div>

    <div class="section">
        <h3>Layer 2: Behavioral Engagement {cold_start_badge}</h3>
        <ul class="eng-list">{eng_items}</ul>
        <div class="formula">
            engagement_score = <strong>{engagement_score:.2f}</strong>
            {'&nbsp;(from population priors — no history available)' if is_cold_start else '&nbsp;(from ML click prediction model)'}
        </div>
    </div>

    <div class="section">
        <h3>Layer 3: Delivery Intelligence</h3>
        <div class="formula">
            priority = 0.65 × urgency + 0.35 × engagement
            = 0.65×{urgency_score:.2f} + 0.35×{engagement_score:.2f}
            = <strong>{intervention_priority:.2f}</strong>
        </div>
        <div class="top-factors">
            <h4>Top Decision Factors</h4>
            <ul>{''.join(f'<li>{html_lib.escape(f)}</li>' for f in top_factors)}</ul>
        </div>
    </div>

    <div class="footer">
        <span>Syngenta IITM Hackathon 2026 — M7 Intelligence Engine</span>
        <span>{'Cold-start mode (population priors)' if is_cold_start else 'Full ML engagement model'}</span>
    </div>
</div>
</body>
</html>"""
    return html
