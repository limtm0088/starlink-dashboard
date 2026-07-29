"""Starlink Mini Kit test-evidence dashboard for IMDA.

Presents field-test data on whether LEO satellite broadband (Starlink Mini)
is technically useful for Singapore use cases, as evidence for a technical
director and management audience.

Tab layout (6 tabs):
    1. Problem Statement  -- headline verdict, readiness, confidence, top
                              implications up front; a "how Starlink Mini
                              works" primer + glossary (collapsed expanders,
                              sourced from Starlink's own spec sheet) so a
                              non-technical reader knows why obstruction is
                              the key metric; download button for a
                              self-contained, printable HTML executive
                              summary (core/report.py).
    2. Methodology         -- data sources, test design, raw data table,
                              CSV/template downloads, calculation methods,
                              a dish-to-dashboard data-pipeline diagram
                              (core/diagrams.py, flags where the throughput
                              unit bug was caught), benchmark reference
                              table (expander, source-linked).
    3. Key Results          -- KPI tiles, per-site comparison chart,
                              per-session time-series (obstruction/ping-drop
                              vs elapsed minutes, to show whether drops
                              cluster or scatter), obstruction-vs-drop
                              scatter, use-case decision table for
                              dense_urban (the only use case with real data).
    4. Risks & Limitations  -- site-type confound (headline risk), partial
                              sessions, single-rig caveat, no live speedtest.
    5. Recommendations      -- use-case scoring matrix + rationale
                              expanders, phased next-steps roadmap table
                              (owner/timing left as placeholders).
    6. AI Q&A                -- rule-based (no API key, no network call) Q&A
                              over the KPI summary + curated knowledge_base.json;
                              unmatched questions are logged for the technical
                              director to answer, then reused automatically.

Real data defaults to loaded on open (data/real_starlink_obstruction_test_data.csv,
697 rows / 4 sessions / 3 sites). A synthetic sample set is available from the
sidebar for exploring the dashboard's shape before/instead of real data --
always labeled SAMPLE/SYNTHETIC, never presented as a measurement.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.thresholds import OBSTRUCTION_BANDS, THRESHOLDS
from config.use_cases import USE_CASES, VERDICT_LABELS
from core import diagrams, qa_engine, report
from core.ingest import IngestError, load_and_validate
from core.metrics import kpi_by_site, kpi_summary
from core.scoring import score_all_use_cases

REAL_DATA_PATH = Path(__file__).parent / "data" / "real_starlink_obstruction_test_data.csv"
SAMPLE_DATA_PATH = Path(__file__).parent / "data" / "sample_starlink_test_data.csv"

VERDICT_COLOR = {
    "suitable": "#1a7f37",
    "marginal": "#9a6700",
    "not_suitable": "#cf222e",
    "insufficient_data": "#6e7781",
}

st.set_page_config(page_title="Starlink Mini — IMDA Evidence Dashboard", layout="wide")


@st.cache_data
def _load(path: str, mtime: float) -> pd.DataFrame:
    return load_and_validate(path)


def load_active_dataset() -> tuple[pd.DataFrame | None, str, str | None]:
    """Returns (dataframe, dataset_label, error_message)."""
    source = st.session_state.get("data_source", "real")

    if source == "upload" and st.session_state.get("uploaded_file") is not None:
        try:
            df = load_and_validate(st.session_state["uploaded_file"])
            return df, "Uploaded file", None
        except IngestError as exc:
            return None, "Uploaded file", str(exc)

    if source == "sample":
        if not SAMPLE_DATA_PATH.exists():
            return None, "Synthetic sample", "Sample dataset not found. Run data/generate_sample_data.py first."
        df = _load(str(SAMPLE_DATA_PATH), SAMPLE_DATA_PATH.stat().st_mtime)
        return df, "SYNTHETIC SAMPLE DATA", None

    if not REAL_DATA_PATH.exists():
        return None, "Real field data", "Real data CSV not found. Run data/convert_real_obstruction_data.py first."
    df = _load(str(REAL_DATA_PATH), REAL_DATA_PATH.stat().st_mtime)
    return df, "Real field data (4 sessions, 3 sites)", None


def render_sidebar() -> None:
    st.sidebar.title("Data source")
    choice = st.sidebar.radio(
        "Dataset",
        options=["real", "sample", "upload"],
        format_func=lambda v: {
            "real": "Real field data (default)",
            "sample": "Synthetic sample data",
            "upload": "Upload a CSV",
        }[v],
        key="data_source",
    )
    if choice == "upload":
        st.sidebar.file_uploader("Upload test-session CSV", type="csv", key="uploaded_file")
        st.sidebar.caption("Must match config/schema.py's required columns.")


def render_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.title("Filters")
    sites = sorted(df["site_name"].dropna().unique())
    selected_sites = st.sidebar.multiselect("Site", sites, default=sites)
    filtered = df[df["site_name"].isin(selected_sites)] if selected_sites else df
    return filtered


def obstruction_band_label(pct: float | None) -> str:
    if pct is None:
        return "n/a"
    for band in OBSTRUCTION_BANDS:
        if pct <= band["max_pct"]:
            return band["label"]
    return OBSTRUCTION_BANDS[-1]["label"]


def render_problem_statement(df: pd.DataFrame, summary: dict, scores: list[dict], label: str) -> None:
    st.header("Problem Statement")
    if label.startswith("SYNTHETIC"):
        st.warning(f"Showing **{label}** — not a real measurement. Switch to real field data in the sidebar.")

    dense_urban = next(r for r in scores if r["use_case"] == "dense_urban")
    verdict = dense_urban["verdict"]
    confidence = dense_urban["confidence"]

    col1, col2, col3 = st.columns(3)
    col1.metric("Headline verdict (dense urban)", VERDICT_LABELS[verdict])
    col2.metric("Confidence", confidence.title())
    col3.metric("Obstruction band", obstruction_band_label(summary.get("avg_obstruction_pct")))

    with st.expander("New to Starlink Mini? How it works, and why \"obstruction\" is the metric that decides everything"):
        st.markdown(
            """
**The hardware** (specs below are Starlink's own published figures, not
this dashboard's measurements): the Mini is a flat phased-array antenna,
298.5 x 259 x 38.5mm, 1.1kg (1.53kg with kickstand and its 15m cable),
drawing 25-40W on average — about the same as a laptop charger. It ships
with an integrated WiFi 5 router (covers up to ~112m² / 1,200 sq ft, up to
128 devices) and a kickstand mount, no separate router or professional
install needed. That portability is exactly why it's a candidate for
emergency-backup and remote-worksite use cases in the first place.

**Why obstruction, specifically, is what this whole test program measures:**
Starlink Mini doesn't point at one fixed spot in the sky like a traditional
satellite dish. It connects to a constellation of Low Earth Orbit (LEO)
satellites at roughly 550km altitude — each one is only visible to a given
ground terminal for about 10 minutes before the connection has to hand off
to the next satellite moving into view. The antenna electronically steers
across a **110° field of view** (Starlink's published spec) to keep
tracking whichever satellite it's currently locked onto. A tree branch,
building overhang, or nearby wall that blocks even part of that 110° cone
can interrupt the link — which is exactly what this rig's `obstruction_pct`
metric is measuring, sample by sample. This is fundamentally different from
cellular (which just needs a nearby tower, no sky view required) or a fixed
GEO satellite dish (which points at one unmoving spot forever) — it's why
this test program's headline number is obstruction, not signal strength or
distance from anything.
            """
        )
        st.plotly_chart(diagrams.build_field_of_view_diagram(), width='stretch', config={"displayModeBar": False})
        st.caption(
            "Source: Starlink's official Mini specification sheet "
            "([starlink.com/public-files/specification_sheet_mini.pdf]"
            "(https://starlink.com/public-files/specification_sheet_mini.pdf)); "
            "LEO altitude/pass-duration figures are general published characteristics "
            "of the Starlink constellation, not vendor-specific claims."
        )

    with st.expander("Glossary of terms used in this dashboard"):
        st.markdown(
            """
- **Obstruction %** — how much of the antenna's 110° field of view is
  currently blocked, as reported by the dish itself.
- **POP latency** — round-trip time from the dish to Starlink's Point of
  Presence (their network edge), in milliseconds. Low even when the link is
  unreliable, since it only measures successful round-trips.
- **Ping drop %** — the share of ping attempts to Starlink's POP that got no
  response at all. The single best indicator of link *stability*, as
  distinct from latency.
- **Probe success %** — combined success rate across independent DNS, HTTP,
  TCP-443, and small-download checks to external destinations — a proxy for
  "would a real request have worked," not just "is the dish connected."
- **Clean sample %** — the share of samples where every probe succeeded
  *and* ping drop was zero — the strictest read of reliability.
- **p95 latency** — the latency value 95% of samples were faster than (i.e.
  worst-case-but-one figure, not the average) — the same percentile
  convention IMDA's own QoS standard uses.
            """
        )

    st.markdown(
        f"""
**Can the Starlink Mini support Singapore dense-urban use cases in its current
tested placements?** Across {summary['n_samples']} samples from
{df['site_name'].nunique()} real sites, average obstruction was
**{summary.get('avg_obstruction_pct', 'n/a')}%** and average Starlink ping drop
was **{summary.get('avg_ping_drop_pct', 'n/a')}%** — {dense_urban['reason']}

**Top 3 implications:**

1. At building sites with high obstruction (HDB home ~72%, MBC office ~55-56%),
   the Mini supports only best-effort, retry-tolerant traffic — not video,
   VPN, or continuous monitoring.
2. The one open-sky test (Punggol Park, ~2.35% obstruction, partial run) looks
   substantially better, but is confounded with site type — see
   **Risks & Limitations**.
3. No IMDA standard specific to satellite broadband exists yet. Against
   IMDA's actual fixed-fibre QoS bar (99.9% availability) as a directional
   reference only, measured probe success (88.2%) falls far short — see
   Methodology for the full caveat on why that's not a compliance finding.
        """
    )

    st.divider()
    st.subheader("Export")
    st.download_button(
        "Download 1-page executive summary (HTML, printable to PDF)",
        report.build_executive_summary_html(df, summary, scores, label),
        file_name="starlink_executive_summary.html",
        mime="text/html",
    )


def render_methodology(df: pd.DataFrame, label: str) -> None:
    st.header("Methodology")
    st.markdown(
        """
**Data source:** a self-hosted Prometheus + Grafana monitoring stack polling
a Starlink Mini dish via gRPC every 3 seconds, with DNS/HTTP/TCP-443/small-download
probes run in parallel (fork of `danopstech/starlink`). Real sessions were
recorded as CSV samples per test window; each session's own `summary.md`/
`decision.md` in the source repo documents the raw verdict this dashboard
re-derives.

**Sessions in this dataset:**
        """
    )
    session_table = (
        df.groupby(["site_name", "location_name"])
        .agg(samples=("timestamp", "count"), start=("timestamp", "min"), end=("timestamp", "max"))
        .reset_index()
    )
    st.dataframe(session_table, width='stretch')

    st.subheader("Data pipeline (dish to dashboard)")
    st.caption(
        "Shown because this pipeline has already produced one silent data error "
        "(the throughput unit bug below) that only manual verification against "
        "the upstream exporter source caught — worth knowing where the numbers "
        "actually come from before trusting them."
    )
    st.plotly_chart(diagrams.build_pipeline_diagram(), width='stretch', config={"displayModeBar": False})

    st.markdown(
        """
**Known data-quality notes:**
- The source rig's `downlink_mbps`/`uplink_mbps` telemetry is idle link
  utilization, not a speedtest result — never mapped into this dashboard's
  `download_mbps`/`upload_mbps` KPI fields. A corrected (unit-bug-fixed)
  version is retained as diagnostic-only `link_utilization_mbps_*` columns.
  (This is the bug flagged in the pipeline diagram above: the PowerShell
  collector trusted a mislabeled Prometheus metric name and applied an
  erroneous extra ×8 conversion — caught by checking the upstream exporter's
  source code, not just its documentation.)
- No live speedtest has been run at any site to date.
        """
    )

    with st.expander("Benchmark reference table (vendor/standards/regulatory figures — not measured)"):
        for key, t in THRESHOLDS.items():
            value = t.get("value", t.get("value_range"))
            comparator = t.get("comparator", "")
            line = f"- **{key}** ({t['source_type']}): {comparator}{value} — _{t['source']}_"
            if t.get("source_url"):
                line += f" [[source]]({t['source_url']})"
            st.markdown(line)

    with st.expander("Raw data + downloads"):
        st.dataframe(df, width='stretch', height=300)
        st.download_button(
            "Download filtered data as CSV",
            df.to_csv(index=False).encode("utf-8"),
            file_name="starlink_filtered_data.csv",
            mime="text/csv",
        )


def render_key_results(df: pd.DataFrame, summary: dict, by_site: pd.DataFrame, scores: list[dict]) -> None:
    st.header("Key Results")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Samples", summary["n_samples"])
    c2.metric("Avg obstruction", f"{summary.get('avg_obstruction_pct', 'n/a')}%")
    c3.metric("Avg ping drop", f"{summary.get('avg_ping_drop_pct', 'n/a')}%")
    c4.metric("Probe success", f"{summary.get('probe_success_pct', 'n/a')}%")
    c5.metric("Clean samples", f"{summary.get('clean_sample_pct', 'n/a')}%")

    st.subheader("Obstruction and ping drop by site")
    fig = go.Figure()
    fig.add_bar(name="Avg obstruction %", x=by_site["site_name"], y=by_site["avg_obstruction_pct"])
    fig.add_bar(name="Avg ping drop %", x=by_site["site_name"], y=by_site["avg_ping_drop_pct"])
    fig.update_layout(barmode="group", yaxis_title="%")
    st.plotly_chart(fig, width='stretch')

    st.subheader("Obstruction and ping drop over time, per session")
    st.caption(
        "Aggregates hide *when* problems happen. This shows whether drops cluster "
        "(e.g. periodic satellite handover) or are scattered randomly across each "
        "test window — a different engineering story either way."
    )
    ts_df = df.copy()
    ts_df["obstruction_pct"] = pd.to_numeric(ts_df["obstruction_pct"], errors="coerce")
    ts_df["pop_drop_pct"] = pd.to_numeric(ts_df["pop_drop_pct"], errors="coerce")
    ts_df["elapsed_min"] = ts_df.groupby("location_name")["timestamp"].transform(
        lambda s: (s - s.min()).dt.total_seconds() / 60
    )
    fig_ts = go.Figure()
    for name, group in ts_df.groupby("location_name"):
        group = group.sort_values("elapsed_min")
        fig_ts.add_scatter(x=group["elapsed_min"], y=group["obstruction_pct"], mode="lines",
                            name=f"{name} — obstruction %", legendgroup=name)
        fig_ts.add_scatter(x=group["elapsed_min"], y=group["pop_drop_pct"], mode="lines",
                            name=f"{name} — ping drop %", legendgroup=name, line=dict(dash="dot"))
    fig_ts.update_layout(xaxis_title="Elapsed minutes since session start", yaxis_title="%",
                          legend=dict(orientation="h", yanchor="bottom", y=1.02))
    st.plotly_chart(fig_ts, width='stretch')

    st.subheader("Obstruction vs. ping drop (sample-level)")
    scatter_df = df.copy()
    scatter_df["obstruction_pct"] = pd.to_numeric(scatter_df["obstruction_pct"], errors="coerce")
    scatter_df["pop_drop_pct"] = pd.to_numeric(scatter_df["pop_drop_pct"], errors="coerce")
    fig2 = px.scatter(
        scatter_df, x="obstruction_pct", y="pop_drop_pct", color="site_name",
        labels={"obstruction_pct": "Obstruction %", "pop_drop_pct": "Ping drop %"},
        opacity=0.6,
    )
    st.plotly_chart(fig2, width='stretch')

    st.subheader("Use-case decision (dense urban — the only use case with real data)")
    dense_urban = next(r for r in scores if r["use_case"] == "dense_urban")
    st.markdown(f"**{VERDICT_LABELS[dense_urban['verdict']]}** ({dense_urban['confidence']} confidence) — {dense_urban['reason']}")

    with st.expander("KPI scoring rubric used above"):
        spec = USE_CASES["dense_urban"]
        st.json(spec)


def render_risks(by_site: pd.DataFrame) -> None:
    st.header("Risks & Limitations")
    st.error(
        """
**Site-type confound (biggest evidence-quality gap):** the 3 real sites
differ in obstruction level AND site type (2 buildings, 1 open park). A
single placement per site cannot separate "better siting technique reduces
obstruction" from "an open park simply has less obstruction than a
building." Do not present the obstruction trend across sites as proof that
siting technique alone fixes obstruction at a building.
        """
    )
    st.markdown(
        """
**Other limitations:**
- **Single rig, single dish:** all data comes from one Starlink Mini unit —
  unit-to-unit or firmware-version variance is not captured.
- **Partial sessions:** the MBC Office session A (2026-06-09 15:04) was
  aborted after ~66 minutes with a mid-session outage window; the Punggol
  Park session (2026-06-25) was stopped early after ~2h21m and also has a
  late outage window (external DNS/HTTP/TCP failures with blank Starlink
  telemetry, ~16:17-16:24). Neither ran the recommended full 4-hour window.
- **No live speedtest:** throughput figures are idle link-utilization
  telemetry, not a measured download/upload capacity.
- **No satellite-specific IMDA standard exists:** the verdicts in this
  dashboard are scored against engineering acceptance criteria authored for
  this test program. IMDA's actual fixed-fibre QoS framework is shown in
  Methodology as a directional reference only — Starlink Mini isn't a
  regulated BASP under it, so any comparison against it is not a compliance
  finding.
        """
    )
    st.subheader("Per-site sample counts (for weighing confidence)")
    st.dataframe(by_site[["site_name", "location_type", "n_samples"]], width='stretch')


def render_recommendations(scores: list[dict]) -> None:
    st.header("Recommendations")

    st.subheader("Use-case fit summary")
    rows = []
    for r in scores:
        rows.append({
            "Use case": r["label"],
            "Verdict": VERDICT_LABELS[r["verdict"]],
            "Confidence": r["confidence"],
            "Basis": r["reason"],
        })
    st.dataframe(pd.DataFrame(rows), width='stretch')

    for r in scores:
        with st.expander(f"Why: {r['label']} — {VERDICT_LABELS[r['verdict']]}"):
            st.write(r["reason"])
            if r["kpis"]:
                st.json(r["kpis"])

    st.subheader("Recommended next steps (roadmap)")
    st.caption("Owner and timing are placeholders — fill in before circulating as a committed plan.")
    roadmap = pd.DataFrame([
        {
            "Phase": "1. Resolve site-type confound",
            "Action": "Run 2-3 placements within the same building (MBC office), full 4-hour sessions each",
            "Owner": "TBD — assign",
            "Target timing": "TBD",
            "Exit criteria": "Obstruction/ping-drop converge toward Punggol-Park levels from repositioning alone, or they don't",
        },
        {
            "Phase": "2. Close the throughput gap",
            "Action": "Run an actual speedtest at the best placement found in Phase 1",
            "Owner": "TBD — assign",
            "Target timing": "TBD, after Phase 1",
            "Exit criteria": "Real download/upload numbers exist to compare against vendor spec",
        },
        {
            "Phase": "3. One full clean run",
            "Action": "Uninterrupted 4-hour test at the best placement, no aborted/outage sessions",
            "Owner": "TBD — assign",
            "Target timing": "TBD, same window as Phase 1-2",
            "Exit criteria": "No outage window; confidence on that placement upgrades to high",
        },
        {
            "Phase": "4. Expand use-case coverage",
            "Action": "Test maritime/port, remote worksite, critical-infra placements (currently insufficient_data)",
            "Owner": "TBD — assign",
            "Target timing": "TBD, after Phase 1 confound is resolved",
            "Exit criteria": "At least one real session per remaining use-case location_type",
        },
        {
            "Phase": "5. Pilot/policy decision",
            "Action": "Bring findings to technical director + management for a go/no-go scope decision",
            "Owner": "TBD — assign",
            "Target timing": "TBD, after Phases 1-3",
            "Exit criteria": "Documented decision, not just another test",
        },
    ])
    st.dataframe(roadmap, width='stretch', hide_index=True)


def render_qa(summary: dict, scores: list[dict], by_site: pd.DataFrame) -> None:
    st.header("AI Q&A")
    st.caption(
        "Rule-based matcher — no API key, no network call, cannot hallucinate. Every answer is either "
        "a previously-approved manual answer or built directly from this dataset's real numbers."
    )

    question = st.text_input("Ask a question about this data")
    if st.button("Ask") and question:
        result = qa_engine.ask(question, summary, scores, by_site)
        if result["answered"]:
            st.success(result["answer"])
            st.caption(f"Source: {result['source']}")
        else:
            st.warning(result["answer"])

    pending = qa_engine.pending_questions()
    if pending:
        st.subheader(f"Answer pending questions ({len(pending)})")
        st.caption("Unmatched questions from past visitors. Answering one saves it for automatic reuse next time it's asked.")
        for q in pending:
            with st.expander(q):
                answer = st.text_area("Your answer", key=f"answer_{q}")
                if st.button("Save answer", key=f"save_{q}") and answer:
                    qa_engine.save_manual_answer(q, answer)
                    st.rerun()

    past = qa_engine.load_past_log()
    if past:
        with st.expander("Full question log"):
            st.dataframe(pd.DataFrame(past), width='stretch')


def main() -> None:
    st.title("Starlink Mini — IMDA Evidence Dashboard")
    render_sidebar()

    df, label, error = load_active_dataset()
    if error:
        st.error(error)
        st.stop()

    df = render_filters(df)
    if df.empty:
        st.warning("No data matches the current filters.")
        st.stop()

    summary = kpi_summary(df)
    by_site = kpi_by_site(df)
    scores = score_all_use_cases(df)

    tabs = st.tabs([
        "Problem Statement", "Methodology", "Key Results",
        "Risks & Limitations", "Recommendations", "AI Q&A",
    ])
    with tabs[0]:
        render_problem_statement(df, summary, scores, label)
    with tabs[1]:
        render_methodology(df, label)
    with tabs[2]:
        render_key_results(df, summary, by_site, scores)
    with tabs[3]:
        render_risks(by_site)
    with tabs[4]:
        render_recommendations(scores)
    with tabs[5]:
        render_qa(summary, scores, by_site)


if __name__ == "__main__":
    main()
