"""The 5 candidate IMDA use cases this dashboard scores Starlink Mini
against, and the engineering acceptance criteria for each.

source_type for every threshold below is "assumption": these are engineering
acceptance criteria authored for this test program (see
.docs/starlink-mini-obstruction-test.md in the source monitoring-system
repo), explicitly NOT official Starlink or IMDA limits. Treat them as a
defensible, explainable starting rubric a technical director can challenge
line by line, not as ground truth.
"""

USE_CASES = {
    "dense_urban": {
        "label": "Dense urban broadband (HDB / office fallback)",
        "applies_to_location_types": ["urban_dense"],
        "min_probe_success_pct": 95,
        "max_ping_drop_pct": 5,
        "max_latency_p95_ms": 500,
    },
    "emergency_backup": {
        "label": "Emergency backup internet",
        "applies_to_location_types": ["urban_dense", "critical_infra", "other"],
        "min_probe_success_pct": 60,
        "max_ping_drop_pct": 40,
        "max_latency_p95_ms": 2000,
    },
    "maritime_port": {
        "label": "Maritime / port connectivity",
        "applies_to_location_types": ["maritime"],
        "min_probe_success_pct": 90,
        "max_ping_drop_pct": 10,
        "max_latency_p95_ms": 500,
    },
    "remote_worksites": {
        "label": "Remote worksite connectivity",
        "applies_to_location_types": ["remote_worksite"],
        "min_probe_success_pct": 90,
        "max_ping_drop_pct": 10,
        "max_latency_p95_ms": 500,
    },
    "critical_infra_backup": {
        "label": "Critical infrastructure backup link",
        "applies_to_location_types": ["critical_infra"],
        "min_probe_success_pct": 98,
        "max_ping_drop_pct": 2,
        "max_latency_p95_ms": 250,
    },
}

VERDICT_LABELS = {
    "suitable": "Suitable",
    "marginal": "Marginal",
    "not_suitable": "Not suitable",
    "insufficient_data": "Insufficient data",
}
