"""Starlink Mini Kit test-evidence dashboard for IMDA.

Presents field-test data on whether LEO satellite broadband (Starlink Mini)
is technically useful for Singapore use cases, as evidence for a technical
director and management audience.

Tab layout (6 tabs):
    1. Problem Statement  -- headline verdict, readiness, confidence, top
                              implications up front.
    2. Methodology         -- data sources, test design, raw data table,
                              CSV/template downloads, calculation methods,
                              benchmark reference table (expander).
    3. Key Results          -- KPI tiles, per-site comparison chart,
                              obstruction-vs-drop scatter, use-case
                              decision table for dense_urban (the only
                              use case with real data).
    4. Risks & Limitations  -- site-type confound (headline risk), partial
                              sessions, single-rig caveat, no live speedtest.
    5. Recommendations      -- use-case scoring matrix + rationale
                              expanders, concrete next-test recommendation.
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
from core import qa_engine
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
3. No IMDA-published regulatory QoS threshold has been applied to this data;
   the verdict above is against engineering acceptance criteria authored for
   this test program, not an official standard.
        """
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

    st.markdown(
        """
**Known data-quality notes:**
- The source rig's `downlink_mbps`/`uplink_mbps` telemetry is idle link
  utilization, not a speedtest result — never mapped into this dashboard's
  `download_mbps`/`upload_mbps` KPI fields. A corrected (unit-bug-fixed)
  version is retained as diagnostic-only `link_utilization_mbps_*` columns.
- No live speedtest has been run at any site to date.
        """
    )

    with st.expander("Benchmark reference table (vendor/standards figures — not measured)"):
        for key, t in THRESHOLDS.items():
            st.markdown(f"- **{key}** ({t['source_type']}): {t.get('value', t.get('value_range'))} — _{t['source']}_")

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
- **No IMDA regulatory QoS threshold applied:** the verdicts in this
  dashboard are scored against engineering acceptance criteria authored for
  this test program, not an official IMDA standard.
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

    st.subheader("Recommended next step")
    st.info(
        """
**Before any pilot or policy recommendation:** run 2-3 placements *within
the same building* (not new sites) — ideally at the MBC office, where a
completed 4-hour baseline already exists for comparison. If obstruction and
ping drop fall to near-Punggol-Park levels purely from repositioning within
one building, that isolates siting technique as the causal factor and
resolves the site-type confound. Also complete one full uninterrupted
4-hour run at the best placement found so far, since both non-HDB sessions
to date are partial.
        """
    )


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
