import pandas as pd
import pytest

from core.metrics import kpi_by_site, kpi_summary, probe_success_pct, clean_sample_pct

DF = pd.DataFrame({
    "timestamp": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-01-01"]),
    "site_name": ["A", "A", "B"],
    "location_type": ["urban_dense", "urban_dense", "maritime"],
    "obstruction_pct": [10, 20, 0],
    "pop_latency_ms": [30, 40, 20],
    "pop_drop_pct": [0, 5, 0],
    "dns_success": ["True", "False", "True"],
    "http_success": ["True", "True", "True"],
    "tcp443_success": ["True", "True", "True"],
    "small_download_success": ["True", "True", "True"],
    "download_mbps": [None, None, None],
    "upload_mbps": [None, None, None],
})


def test_kpi_summary_computes_expected_fields():
    summary = kpi_summary(DF)
    assert summary["n_samples"] == 3
    assert summary["avg_obstruction_pct"] == 10.0
    assert summary["max_obstruction_pct"] == 20
    assert summary["avg_download_mbps"] is None


def test_probe_success_pct_partial_failure():
    pct = probe_success_pct(DF)
    assert 0 < pct < 100


def test_clean_sample_pct_requires_zero_drop():
    pct = clean_sample_pct(DF)
    # row 0: all probes true, drop 0 -> clean; row1: dns false -> not clean; row2: clean
    assert pct == pytest.approx(66.67, abs=0.1)


def test_kpi_by_site_groups_correctly():
    by_site = kpi_by_site(DF)
    assert set(by_site["site_name"]) == {"A", "B"}
    assert by_site.set_index("site_name").loc["B", "n_samples"] == 1
