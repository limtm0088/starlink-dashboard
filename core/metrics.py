"""KPI aggregation. Every function here computes a MEASURED value from the
loaded dataframe -- nothing in this module invents or assumes a number.
"""
from __future__ import annotations

import pandas as pd

CLEAN_COLUMNS = ["dns_success", "http_success", "tcp443_success", "small_download_success"]


def _to_bool_series(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s
    return s.astype(str).str.strip().str.lower().map({"true": True, "false": False})


def probe_success_pct(df: pd.DataFrame) -> float | None:
    """Combined availability across every external probe channel that has data."""
    present = [c for c in CLEAN_COLUMNS if c in df.columns and df[c].notna().any()]
    if not present:
        return None
    bools = pd.concat([_to_bool_series(df[c]) for c in present], axis=1)
    return round(bools.mean(axis=1).mean() * 100, 2)


def clean_sample_pct(df: pd.DataFrame) -> float | None:
    """Rows where every present probe channel succeeded AND ping drop was 0."""
    present = [c for c in CLEAN_COLUMNS if c in df.columns and df[c].notna().any()]
    if not present:
        return None
    bools = pd.concat([_to_bool_series(df[c]) for c in present], axis=1)
    all_clean = bools.all(axis=1)
    if "pop_drop_pct" in df.columns and df["pop_drop_pct"].notna().any():
        no_drop = pd.to_numeric(df["pop_drop_pct"], errors="coerce").fillna(100) == 0
        all_clean = all_clean & no_drop
    return round(all_clean.mean() * 100, 2)


def kpi_summary(df: pd.DataFrame) -> dict:
    """One row of headline KPIs for the whole (already-filtered) dataframe."""
    summary: dict = {"n_samples": len(df)}

    if "obstruction_pct" in df.columns and df["obstruction_pct"].notna().any():
        obstruction = pd.to_numeric(df["obstruction_pct"], errors="coerce")
        summary["avg_obstruction_pct"] = round(obstruction.mean(), 2)
        summary["max_obstruction_pct"] = round(obstruction.max(), 2)
    else:
        summary["avg_obstruction_pct"] = None
        summary["max_obstruction_pct"] = None

    if "pop_latency_ms" in df.columns and df["pop_latency_ms"].notna().any():
        latency = pd.to_numeric(df["pop_latency_ms"], errors="coerce").dropna()
        summary["avg_latency_ms"] = round(latency.mean(), 2)
        summary["p95_latency_ms"] = round(latency.quantile(0.95), 2) if len(latency) else None
    else:
        summary["avg_latency_ms"] = None
        summary["p95_latency_ms"] = None

    if "pop_drop_pct" in df.columns and df["pop_drop_pct"].notna().any():
        drop = pd.to_numeric(df["pop_drop_pct"], errors="coerce")
        summary["avg_ping_drop_pct"] = round(drop.mean(), 2)
    else:
        summary["avg_ping_drop_pct"] = None

    summary["probe_success_pct"] = probe_success_pct(df)
    summary["clean_sample_pct"] = clean_sample_pct(df)

    for col in ("download_mbps", "upload_mbps"):
        if col in df.columns and df[col].notna().any():
            summary[f"avg_{col}"] = round(pd.to_numeric(df[col], errors="coerce").mean(), 2)
        else:
            summary[f"avg_{col}"] = None

    return summary


def kpi_by_site(df: pd.DataFrame) -> pd.DataFrame:
    """kpi_summary() grouped by site_name, for the site-comparison chart."""
    rows = []
    for site, group in df.groupby("site_name"):
        row = {"site_name": site, "location_type": group["location_type"].iloc[0]}
        row.update(kpi_summary(group))
        rows.append(row)
    return pd.DataFrame(rows).sort_values("avg_obstruction_pct", na_position="last")
