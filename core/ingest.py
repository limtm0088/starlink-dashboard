"""Validates an uploaded/loaded CSV against config/schema.py before anything
else in the app is allowed to touch it.
"""
from __future__ import annotations

import pandas as pd

from config.schema import ALL_COLUMNS, KPI_COLUMNS, LOCATION_TYPES, REQUIRED_COLUMNS, TEST_TYPES


class IngestError(Exception):
    """Raised when a CSV fails schema validation. Message is user-facing."""


def load_and_validate(path_or_buffer) -> pd.DataFrame:
    try:
        df = pd.read_csv(path_or_buffer)
    except Exception as exc:  # pandas raises many exception types on bad CSVs
        raise IngestError(f"Could not read file as CSV: {exc}") from exc

    missing_required = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_required:
        raise IngestError(
            "Missing required column(s): " + ", ".join(missing_required)
        )

    present_kpis = [c for c in KPI_COLUMNS if c in df.columns]
    if not present_kpis:
        raise IngestError(
            "No recognized KPI columns found. Expected at least one of: "
            + ", ".join(KPI_COLUMNS)
        )

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    bad_timestamps = df["timestamp"].isna().sum()
    if bad_timestamps:
        raise IngestError(f"{bad_timestamps} row(s) have an unparseable timestamp.")

    bad_location_type = ~df["location_type"].isin(LOCATION_TYPES)
    if bad_location_type.any():
        bad_values = sorted(df.loc[bad_location_type, "location_type"].unique())
        raise IngestError(
            "Unrecognized location_type value(s): "
            + ", ".join(str(v) for v in bad_values)
            + f". Allowed: {', '.join(LOCATION_TYPES)}"
        )

    bad_test_type = ~df["test_type"].isin(TEST_TYPES)
    if bad_test_type.any():
        bad_values = sorted(df.loc[bad_test_type, "test_type"].unique())
        raise IngestError(
            "Unrecognized test_type value(s): "
            + ", ".join(str(v) for v in bad_values)
            + f". Allowed: {', '.join(TEST_TYPES)}"
        )

    if "obstruction_pct" in df.columns:
        obstruction = pd.to_numeric(df["obstruction_pct"], errors="coerce")
        out_of_range = obstruction.notna() & ((obstruction < 0) | (obstruction > 100))
        if out_of_range.any():
            raise IngestError(
                f"{int(out_of_range.sum())} row(s) have obstruction_pct outside 0-100."
            )

    dropped = df[present_kpis].isna().all(axis=1).sum()
    if dropped:
        df = df[~df[present_kpis].isna().all(axis=1)].copy()

    extra_cols = [c for c in ALL_COLUMNS if c not in df.columns]
    for c in extra_cols:
        df[c] = pd.NA

    return df.reset_index(drop=True)
