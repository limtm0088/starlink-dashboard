"""Data contract for Starlink test-session CSVs ingested by this dashboard.

Any CSV uploaded (real field data or the synthetic sample set) must satisfy
this schema before it reaches scoring or the UI.
"""

# Columns every row must have, non-null.
REQUIRED_COLUMNS = [
    "timestamp",
    "site_name",
    "location_name",
    "location_type",
    "test_type",
]

# Columns that carry the actual telemetry. Individually optional (a row can
# be missing e.g. a speedtest if none was run) but at least one KPI column
# must be present per row or the row is dropped as unusable.
KPI_COLUMNS = [
    "obstruction_pct",
    "currently_obstructed",
    "pop_latency_ms",
    "pop_drop_pct",
    "dns_success",
    "http_success",
    "tcp443_success",
    "small_download_success",
    "download_mbps",
    "upload_mbps",
]

# Diagnostic-only columns. Never used for scoring or KPI headlines because
# they are not a real speedtest result (see link_utilization_mbps_* below).
DIAGNOSTIC_COLUMNS = [
    "link_utilization_mbps_down",
    "link_utilization_mbps_up",
]

ALL_COLUMNS = REQUIRED_COLUMNS + KPI_COLUMNS + DIAGNOSTIC_COLUMNS

LOCATION_TYPES = [
    "urban_dense",
    "maritime",
    "remote_worksite",
    "critical_infra",
    "other",
]

TEST_TYPES = [
    "obstruction_stability",
    "speedtest",
    "latency_sweep",
]

# source_type tags used throughout config/thresholds.py so a reader can
# never confuse a measured finding with a vendor claim or a regulatory
# figure -- every threshold in this app must carry one of these.
SOURCE_TYPES = [
    "measured",             # computed directly from this rig's own samples
    "vendor_spec",          # Starlink's own published spec sheet
    "standards_reference",  # 3GPP/ITU/ISO etc.
    "regulatory_reference",  # IMDA or another body with enforcement authority
    "assumption",           # engineering acceptance criteria authored for
                             # this test program, not an official limit
]
