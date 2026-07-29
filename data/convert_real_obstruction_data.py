"""Converts the 4 real obstruction-test sessions from the source monitoring
rig (`starlink monitoring system/data/obstruction-tests/<timestamp>/samples.csv`)
into this dashboard's schema (config/schema.py).

Run from anywhere:
    python data/convert_real_obstruction_data.py

Site mapping (do not change without re-checking the source session docs --
see project memory "Site-type confound" note): these are 3 distinct real
sites, NOT one site repositioned. 20260609-150425 and 20260609-162441 are
the same MBC Office placement, same day (an earlier partial/aborted attempt
and the completed 4-hour run).
"""
from __future__ import annotations

import csv
from pathlib import Path

SOURCE_ROOT = (
    Path(__file__).resolve().parents[3]
    / "starlink monitoring system"
    / "data"
    / "obstruction-tests"
)

OUTPUT_PATH = Path(__file__).resolve().parent / "real_starlink_obstruction_test_data.csv"

SESSIONS = [
    {
        "folder": "20260519-111841",
        "site_name": "HDB Home",
        "location_name": "HDB Home - Placement 1",
        "note": "Baseline placement, heavily obstructed",
    },
    {
        "folder": "20260609-150425",
        "site_name": "MBC Office",
        "location_name": "MBC Office - Placement 2 (session A, partial/aborted)",
        "note": "Short run, contains a mid-session outage window",
    },
    {
        "folder": "20260609-162441",
        "site_name": "MBC Office",
        "location_name": "MBC Office - Placement 2 (session B, completed)",
        "note": "Completed 4-hour run",
    },
    {
        "folder": "20260625-140421",
        "site_name": "Punggol Park",
        "location_name": "Punggol Park - Placement 3 (partial, stopped early)",
        "note": "Open sky, stopped early by request; late outage window",
    },
]

# location_type is urban_dense for all 3 real sites, including Punggol Park
# (an open park, not a building) -- this is the user's explicit call, not a
# schema mismatch. The site-type confound is handled via site_name +
# narrative caveats in the app, not a new location_type category.
LOCATION_TYPE = "urban_dense"
TEST_TYPE = "obstruction_stability"

OUTPUT_COLUMNS = [
    "timestamp", "site_name", "location_name", "location_type", "test_type",
    "obstruction_pct", "currently_obstructed", "pop_latency_ms", "pop_drop_pct",
    "dns_success", "http_success", "tcp443_success", "small_download_success",
    "download_mbps", "upload_mbps",
    "link_utilization_mbps_down", "link_utilization_mbps_up",
]


def _bool(v: str) -> str:
    return "True" if str(v).strip().lower() == "true" else "False"


def _fix_throughput(raw_mbps: str) -> str:
    """The source rig's downlink_mbps/uplink_mbps columns are computed from
    a Prometheus metric whose HELP text claims bytes/sec but whose value is
    actually already bits/sec (see danopstech/starlink_exporter's
    exporter.go: the gauge is set from GetDownlinkThroughputBps() with no
    conversion). The source PowerShell collector trusted the metric name and
    multiplied by 8 to get Mbps, an erroneous extra x8. Divide back out.
    Verified against upstream exporter.go/dish.pb.go, not just docs -- do
    not re-introduce the x8 without re-checking that source again.
    """
    try:
        return str(float(raw_mbps) / 8)
    except (TypeError, ValueError):
        return ""


def convert() -> int:
    rows_written = 0
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()

        for session in SESSIONS:
            src = SOURCE_ROOT / session["folder"] / "samples.csv"
            if not src.exists():
                raise FileNotFoundError(f"Expected source file not found: {src}")

            with src.open(encoding="utf-8-sig") as in_f:
                for row in csv.DictReader(in_f):
                    if not row.get("timestamp"):
                        continue
                    writer.writerow({
                        "timestamp": row["timestamp"],
                        "site_name": session["site_name"],
                        "location_name": session["location_name"],
                        "location_type": LOCATION_TYPE,
                        "test_type": TEST_TYPE,
                        "obstruction_pct": row.get("obstruction_pct", ""),
                        "currently_obstructed": _bool(row.get("currently_obstructed", "")),
                        "pop_latency_ms": row.get("pop_latency_ms", ""),
                        "pop_drop_pct": row.get("pop_drop_pct", ""),
                        "dns_success": _bool(row.get("dns_success", "")),
                        "http_success": _bool(row.get("http_success", "")),
                        "tcp443_success": _bool(row.get("tcp_443_success", "")),
                        "small_download_success": _bool(row.get("small_download_success", "")),
                        # Deliberately blank: the source has never run a real
                        # speedtest (see .docs/starlink-mini-obstruction-test.md
                        # "Speedtest: Not run yet"). Do not map
                        # downlink_mbps/uplink_mbps here -- that would
                        # misrepresent idle link-utilization telemetry as
                        # throughput capacity.
                        "download_mbps": "",
                        "upload_mbps": "",
                        "link_utilization_mbps_down": _fix_throughput(row.get("downlink_mbps", "")),
                        "link_utilization_mbps_up": _fix_throughput(row.get("uplink_mbps", "")),
                    })
                    rows_written += 1

    return rows_written


if __name__ == "__main__":
    n = convert()
    print(f"Wrote {n} rows to {OUTPUT_PATH}")
