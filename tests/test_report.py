import pandas as pd

from core.report import build_executive_summary_html

DF = pd.DataFrame({"site_name": ["HDB Home", "Punggol Park"]})

SUMMARY = {"n_samples": 697, "avg_obstruction_pct": 53.97, "avg_ping_drop_pct": 27.67}

SCORES = [
    {"use_case": "dense_urban", "label": "Dense urban broadband", "verdict": "not_suitable",
     "confidence": "high", "reason": "ping drop too high", "kpis": {}},
    {"use_case": "emergency_backup", "label": "Emergency backup internet", "verdict": "suitable",
     "confidence": "high", "reason": "meets criteria", "kpis": {}},
]


def test_report_is_self_contained_html():
    html = build_executive_summary_html(DF, SUMMARY, SCORES, "Real field data")
    assert html.startswith("<!doctype html>")
    assert "</html>" in html


def test_report_includes_real_kpi_numbers_not_placeholders():
    html = build_executive_summary_html(DF, SUMMARY, SCORES, "Real field data")
    assert "53.97" in html
    assert "27.67" in html
    assert "697" in html


def test_report_includes_every_use_case_row():
    html = build_executive_summary_html(DF, SUMMARY, SCORES, "Real field data")
    assert "Dense urban broadband" in html
    assert "Emergency backup internet" in html
