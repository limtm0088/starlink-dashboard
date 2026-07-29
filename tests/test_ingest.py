import io

import pytest

from core.ingest import IngestError, load_and_validate

VALID_CSV = (
    "timestamp,site_name,location_name,location_type,test_type,obstruction_pct,"
    "pop_latency_ms,pop_drop_pct,dns_success,http_success,tcp443_success,small_download_success\n"
    "2026-01-01 00:00:00,Site A,Site A - P1,urban_dense,obstruction_stability,10,30,1,True,True,True,True\n"
    "2026-01-01 00:01:00,Site A,Site A - P1,urban_dense,obstruction_stability,12,31,2,True,True,True,True\n"
)


def test_valid_csv_loads():
    df = load_and_validate(io.StringIO(VALID_CSV))
    assert len(df) == 2
    assert "site_name" in df.columns


def test_missing_required_column_raises():
    bad = VALID_CSV.replace("location_type,", "")
    with pytest.raises(IngestError, match="Missing required column"):
        load_and_validate(io.StringIO(bad))


def test_bad_location_type_raises():
    bad = VALID_CSV.replace("urban_dense", "not_a_real_type")
    with pytest.raises(IngestError, match="Unrecognized location_type"):
        load_and_validate(io.StringIO(bad))


def test_obstruction_out_of_range_raises():
    bad = VALID_CSV.replace(",10,", ",150,")
    with pytest.raises(IngestError, match="obstruction_pct outside"):
        load_and_validate(io.StringIO(bad))


def test_unparseable_timestamp_raises():
    bad = VALID_CSV.replace("2026-01-01 00:00:00", "not-a-date")
    with pytest.raises(IngestError, match="unparseable timestamp"):
        load_and_validate(io.StringIO(bad))


def test_no_kpi_columns_raises():
    bad = "timestamp,site_name,location_name,location_type,test_type\n2026-01-01,Site A,P1,urban_dense,obstruction_stability\n"
    with pytest.raises(IngestError, match="No recognized KPI columns"):
        load_and_validate(io.StringIO(bad))
