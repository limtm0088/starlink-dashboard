"""Builds a self-contained, printable HTML executive summary from live
dashboard data. Recipients open it in any browser and print-to-PDF (Ctrl+P)
-- no PDF library dependency, no server-side rendering needed.
"""
from __future__ import annotations

from datetime import datetime, timezone

from config.use_cases import VERDICT_LABELS

CSS = """
<style>
  body { font-family: -apple-system, Segoe UI, Arial, sans-serif; max-width: 760px;
         margin: 40px auto; color: #1a1a1a; line-height: 1.5; }
  h1 { font-size: 22px; border-bottom: 3px solid #1a1a1a; padding-bottom: 8px; }
  h2 { font-size: 16px; margin-top: 28px; color: #333; }
  .verdict-band { display: flex; gap: 24px; margin: 16px 0; }
  .verdict-band div { flex: 1; border: 1px solid #ddd; border-radius: 6px; padding: 10px 14px; }
  .verdict-band .label { font-size: 11px; text-transform: uppercase; color: #666; }
  .verdict-band .value { font-size: 20px; font-weight: 600; }
  .not_suitable { color: #cf222e; }
  .marginal { color: #9a6700; }
  .suitable { color: #1a7f37; }
  .insufficient_data { color: #6e7781; }
  table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 13px; }
  th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; }
  th { background: #f4f4f4; }
  .caveat { background: #fff8e1; border-left: 4px solid #9a6700; padding: 8px 12px; font-size: 13px; margin: 10px 0; }
  .risk { background: #fdeceb; border-left: 4px solid #cf222e; padding: 8px 12px; font-size: 13px; margin: 10px 0; }
  footer { margin-top: 30px; font-size: 11px; color: #888; border-top: 1px solid #ddd; padding-top: 8px; }
  @media print { body { margin: 0; max-width: none; } }
</style>
"""


def _fmt(v) -> str:
    return "n/a" if v is None else str(v)


def build_executive_summary_html(df, kpi_summary: dict, use_case_scores: list[dict], label: str) -> str:
    dense_urban = next(r for r in use_case_scores if r["use_case"] == "dense_urban")
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    rows = "".join(
        f"<tr><td>{r['label']}</td><td class='{r['verdict']}'>{VERDICT_LABELS[r['verdict']]}</td>"
        f"<td>{r['confidence']}</td><td>{r['reason']}</td></tr>"
        for r in use_case_scores
    )

    sites = ", ".join(sorted(df["site_name"].dropna().unique()))

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Starlink Mini — Executive Summary</title>
{CSS}
</head><body>
<h1>Starlink Mini — IMDA Evidence Summary</h1>
<p style="color:#666; font-size:13px;">Dataset: {label} &middot; Generated {generated}</p>

<div class="verdict-band">
  <div><div class="label">Headline verdict (dense urban)</div>
       <div class="value {dense_urban['verdict']}">{VERDICT_LABELS[dense_urban['verdict']]}</div></div>
  <div><div class="label">Confidence</div><div class="value">{dense_urban['confidence'].title()}</div></div>
  <div><div class="label">Samples</div><div class="value">{kpi_summary['n_samples']}</div></div>
</div>

<h2>Bottom line</h2>
<p>Across {kpi_summary['n_samples']} samples from {df['site_name'].nunique()} real Singapore sites
({sites}), average obstruction was <b>{_fmt(kpi_summary.get('avg_obstruction_pct'))}%</b> and average
Starlink ping drop was <b>{_fmt(kpi_summary.get('avg_ping_drop_pct'))}%</b>. {dense_urban['reason']}</p>

<h2>Use-case fit</h2>
<table>
<tr><th>Use case</th><th>Verdict</th><th>Confidence</th><th>Basis</th></tr>
{rows}
</table>

<h2>Biggest evidence-quality risk</h2>
<div class="risk">The 3 real sites differ in both obstruction level AND site type (2 buildings, 1 open
park). A single placement per site cannot separate "better siting technique reduces obstruction" from
"an open park simply has less obstruction than a building." Do not treat the obstruction trend across
sites as proof siting technique alone fixes the problem at a building.</div>

<h2>Regulatory context</h2>
<div class="caveat">IMDA has no QoS standard specific to satellite broadband. Its fixed-fibre standard
(99.9% availability, &le;30ms local latency) is shown elsewhere in this dashboard only as a directional
reference — Starlink Mini is not a regulated BASP under that framework, so this is not a compliance
finding.</div>

<h2>Recommended next step</h2>
<p>Run 2-3 placements within the same building (not new sites) before any pilot or policy
recommendation — this is the only way to isolate siting technique from the site-type confound above.
See the Recommendations tab in the live dashboard for the full phased plan.</p>

<footer>Generated from the Starlink Mini IMDA Evidence Dashboard. Real field data, not vendor claims.
Print this page (Ctrl+P) to save as PDF.</footer>
</body></html>"""
