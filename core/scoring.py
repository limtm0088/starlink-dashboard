"""Explainable (non-ML) scoring rubric: for each of the 5 candidate use
cases, compare this dataset's measured KPIs against config/use_cases.py's
acceptance criteria and return a verdict + the reasoning behind it.

A use case scores "insufficient_data" rather than a fabricated verdict when
this dataset has no rows at a matching location_type -- never guess.
"""
from __future__ import annotations

from config.use_cases import USE_CASES
from core.metrics import kpi_summary


def score_use_case(df, use_case_key: str) -> dict:
    spec = USE_CASES[use_case_key]
    matching = df[df["location_type"].isin(spec["applies_to_location_types"])]

    if matching.empty:
        return {
            "use_case": use_case_key,
            "label": spec["label"],
            "verdict": "insufficient_data",
            "confidence": "n/a",
            "reason": (
                f"No test sessions at a location_type in "
                f"{spec['applies_to_location_types']} exist in this dataset."
            ),
            "kpis": {},
        }

    kpis = kpi_summary(matching)
    failures = []

    if kpis["probe_success_pct"] is not None and kpis["probe_success_pct"] < spec["min_probe_success_pct"]:
        failures.append(
            f"probe success {kpis['probe_success_pct']}% < required {spec['min_probe_success_pct']}%"
        )
    if kpis["avg_ping_drop_pct"] is not None and kpis["avg_ping_drop_pct"] > spec["max_ping_drop_pct"]:
        failures.append(
            f"ping drop {kpis['avg_ping_drop_pct']}% > allowed {spec['max_ping_drop_pct']}%"
        )
    if kpis["p95_latency_ms"] is not None and kpis["p95_latency_ms"] > spec["max_latency_p95_ms"]:
        failures.append(
            f"p95 latency {kpis['p95_latency_ms']}ms > allowed {spec['max_latency_p95_ms']}ms"
        )

    if not failures:
        verdict = "suitable"
    elif len(failures) == 1:
        verdict = "marginal"
    else:
        verdict = "not_suitable"

    n_sites = matching["site_name"].nunique()
    confidence = "high" if n_sites >= 2 and kpis["n_samples"] >= 100 else "low"

    reason = "; ".join(failures) if failures else "All acceptance criteria met."

    return {
        "use_case": use_case_key,
        "label": spec["label"],
        "verdict": verdict,
        "confidence": confidence,
        "reason": reason,
        "kpis": kpis,
    }


def score_all_use_cases(df) -> list[dict]:
    return [score_use_case(df, key) for key in USE_CASES]
