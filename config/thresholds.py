"""Every comparison baseline used anywhere in this dashboard, tagged by
source_type so a measured finding is never visually conflated with a vendor
claim, a standards figure, or a regulatory limit.

IMPORTANT applicability caveat for the "regulatory_reference" entries below:
IMDA has not published a QoS standard specific to satellite/wireless
broadband. The entries here come from IMDA's actual "Quality of Service
Framework for Retail Fixed-Line Broadband Internet Access Services (Fibre
Broadband Services)" (verified 2026-07-29 against IMDA's own published PDF,
see source_url on each entry) -- which legally applies only to fixed-line
fibre Broadband Access Service Providers with >=10% market share. Starlink
Mini is neither fixed-line nor a regulated BASP under this framework, so
these numbers are NOT a compliance bar Starlink must clear. They're used
here only as the closest official "what does acceptable broadband look
like in Singapore" reference point a technical director can sanity-check
this data against. Measurement methodology also differs: IMDA's standard is
5-minute test calls during the 4 busiest hours/day, 95th-percentile
monthly; this rig is continuous 3-second polling. Do not present any
comparison against these figures as a compliance finding.
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
    "imda_fixed_fibre_availability_pct": {
        "value": 99.9,
        "comparator": ">=",
        "source_type": "regulatory_reference",
        "source": (
            "IMDA QoS Framework for Retail Fixed-Line Broadband (Fibre) -- compliance "
            "standard for BASPs with >=10% market share. NOT a satellite/wireless "
            "standard -- directional reference only, see module docstring."
        ),
        "source_url": "https://www.imda.gov.sg/-/media/imda/files/regulation-licensing-and-consultations/licensing/licenses/compliance-to-ida-standards/page-b---qos-framework-for-fibre-broadband-services.pdf",
    },
    "imda_fixed_fibre_local_latency_ms": {
        "value": 30,
        "comparator": "<=",
        "source_type": "regulatory_reference",
        "source": (
            "IMDA QoS Framework for Fibre Broadband -- local round-trip latency, "
            "95th percentile during the 4 busiest hours/day. Same applicability "
            "caveat as above."
        ),
        "source_url": "https://www.imda.gov.sg/-/media/imda/files/regulation-licensing-and-consultations/licensing/licenses/compliance-to-ida-standards/page-b---qos-framework-for-fibre-broadband-services.pdf",
    },
    "imda_fixed_fibre_intl_latency_ms": {
        "value": 300,
        "comparator": "<=",
        "source_type": "regulatory_reference",
        "source": (
            "IMDA QoS Framework for Fibre Broadband -- international round-trip "
            "latency, 95th percentile during peak hours. Same applicability caveat."
        ),
        "source_url": "https://www.imda.gov.sg/-/media/imda/files/regulation-licensing-and-consultations/licensing/licenses/compliance-to-ida-standards/page-b---qos-framework-for-fibre-broadband-services.pdf",
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
