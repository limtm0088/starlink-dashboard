import pandas as pd

from core.scoring import score_all_use_cases, score_use_case

GOOD_DF = pd.DataFrame({
    "timestamp": pd.to_datetime(["2026-01-01"] * 4),
    "site_name": ["A", "A", "B", "B"],
    "location_type": ["urban_dense"] * 4,
    "obstruction_pct": [1, 1, 1, 1],
    "pop_latency_ms": [20, 20, 20, 20],
    "pop_drop_pct": [0, 0, 0, 0],
    "dns_success": ["True"] * 4,
    "http_success": ["True"] * 4,
    "tcp443_success": ["True"] * 4,
    "small_download_success": ["True"] * 4,
    "download_mbps": [None] * 4,
    "upload_mbps": [None] * 4,
})

BAD_DF = GOOD_DF.copy()
BAD_DF["pop_drop_pct"] = [50, 50, 50, 50]
BAD_DF["dns_success"] = ["False"] * 4


def test_suitable_when_all_criteria_met():
    result = score_use_case(GOOD_DF, "dense_urban")
    assert result["verdict"] == "suitable"


def test_not_suitable_when_multiple_criteria_fail():
    result = score_use_case(BAD_DF, "dense_urban")
    assert result["verdict"] == "not_suitable"
    assert "ping drop" in result["reason"]


def test_insufficient_data_when_no_matching_location_type():
    result = score_use_case(GOOD_DF, "maritime_port")
    assert result["verdict"] == "insufficient_data"
    assert result["confidence"] == "n/a"


def test_score_all_use_cases_covers_every_use_case():
    results = score_all_use_cases(GOOD_DF)
    assert len(results) == 5
    keys = {r["use_case"] for r in results}
    assert keys == {"dense_urban", "emergency_backup", "maritime_port", "remote_worksites", "critical_infra_backup"}
