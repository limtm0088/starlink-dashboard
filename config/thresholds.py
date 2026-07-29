"""Every comparison baseline used anywhere in this dashboard, tagged by
source_type so a measured finding is never visually conflated with a vendor
claim, a standards figure, or a regulatory limit.

IMPORTANT: this app applies NO official IMDA regulatory QoS threshold. IMDA
has not published a specific numeric standard this test program can cite
for residential/enterprise LEO broadband obstruction tolerance, so nothing
here is tagged "regulatory_reference" -- that is a deliberate gap, flagged
in the Risks & Limitations tab, not an oversight. If the technical director
has an internal IMDA benchmark to apply, wire it in here rather than
guessing at a number.
"""

THRESHOLDS = {
    "starlink_vendor_download_mbps": {
        "value_range": (25, 220),
        "source_type": "vendor_spec",
        "source": "Starlink public residential/roam spec sheet (typical range, varies by plan and congestion)",
    },
    "starlink_vendor_upload_mbps": {
        "value_range": (5, 20),
        "source_type": "vendor_spec",
        "source": "Starlink public residential/roam spec sheet",
    },
    "starlink_vendor_latency_ms": {
        "value_range": (25, 60),
        "source_type": "vendor_spec",
        "source": "Starlink public spec sheet (typical, non-obstructed)",
    },
    "leo_ntn_latency_budget_ms": {
        "value": 35,
        "source_type": "standards_reference",
        "source": "3GPP TR 38.821 -- LEO NTN one-way latency budget (~30-35ms)",
    },
    "itu_class0_delay_jitter_loss": {
        "value": "delay <=100ms, jitter <=50ms, loss <=1e-3",
        "source_type": "standards_reference",
        "source": "ITU-T Y.1541 Class 0 (real-time, jitter-sensitive, high interaction)",
    },
}

# Engineering acceptance bands used to interpret obstruction levels.
# Authored for this test program by the person running the rig -- these are
# NOT official Starlink or IMDA limits. See .docs/starlink-mini-obstruction-test.md
# in the source monitoring-system repo for the original definitions.
OBSTRUCTION_BANDS = [
    {"max_pct": 2, "label": "Good", "note": "Most normal uses, including calls and remote work", "source_type": "assumption"},
    {"max_pct": 5, "label": "Usually usable", "note": "Browsing, streaming, calls may be okay; monitor drops", "source_type": "assumption"},
    {"max_pct": 15, "label": "Degraded", "note": "Browsing, messaging, downloads; real-time use becomes risky", "source_type": "assumption"},
    {"max_pct": 30, "label": "Poor", "note": "Basic browsing, messaging, emergency use only", "source_type": "assumption"},
    {"max_pct": 100, "label": "Very poor", "note": "Noncritical, asynchronous, retry-friendly workloads only", "source_type": "assumption"},
]
