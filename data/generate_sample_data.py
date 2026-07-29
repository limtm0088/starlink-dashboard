"""Generates a synthetic sample dataset so the dashboard is explorable
before/without real IMDA test data. Always labeled SAMPLE/SYNTHETIC in the
UI (app.py checks the label) -- never to be cited as a real measurement.
"""
from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

OUTPUT_PATH = Path(__file__).resolve().parent / "sample_starlink_test_data.csv"

SITES = [
    {"site_name": "Sample Dense Urban Site", "location_type": "urban_dense", "obstruction_mean": 40},
    {"site_name": "Sample Maritime Site", "location_type": "maritime", "obstruction_mean": 5},
    {"site_name": "Sample Remote Worksite", "location_type": "remote_worksite", "obstruction_mean": 10},
    {"site_name": "Sample Critical Infra Site", "location_type": "critical_infra", "obstruction_mean": 3},
]

COLUMNS = [
    "timestamp", "site_name", "location_name", "location_type", "test_type",
    "obstruction_pct", "currently_obstructed", "pop_latency_ms", "pop_drop_pct",
    "dns_success", "http_success", "tcp443_success", "small_download_success",
    "download_mbps", "upload_mbps",
    "link_utilization_mbps_down", "link_utilization_mbps_up",
]


def generate() -> int:
    rows = []
    start = datetime(2026, 1, 1, 9, 0, 0)
    for site in SITES:
        for i in range(150):
            ts = start + timedelta(minutes=i)
            obstruction = max(0, min(100, random.gauss(site["obstruction_mean"], 8)))
            drop = max(0, min(100, obstruction * 0.5 + random.gauss(0, 3)))
            success = random.random() > (drop / 150)
            rows.append({
                "timestamp": ts.isoformat(sep=" "),
                "site_name": site["site_name"],
                "location_name": f"{site['site_name']} - Placement 1",
                "location_type": site["location_type"],
                "test_type": "obstruction_stability",
                "obstruction_pct": round(obstruction, 2),
                "currently_obstructed": "True" if obstruction > 2 else "False",
                "pop_latency_ms": round(random.gauss(30, 5), 2),
                "pop_drop_pct": round(drop, 2),
                "dns_success": str(success),
                "http_success": str(success),
                "tcp443_success": str(success),
                "small_download_success": str(success),
                "download_mbps": round(random.gauss(120, 40), 2),
                "upload_mbps": round(random.gauss(12, 4), 2),
                "link_utilization_mbps_down": round(random.gauss(15, 5), 2),
                "link_utilization_mbps_up": round(random.gauss(2, 1), 2),
            })

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return len(rows)


if __name__ == "__main__":
    n = generate()
    print(f"Wrote {n} synthetic rows to {OUTPUT_PATH}")
