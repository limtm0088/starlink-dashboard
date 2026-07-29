import json

import pandas as pd
import pytest

from core import qa_engine

SUMMARY = {
    "n_samples": 697,
    "avg_obstruction_pct": 53.97,
    "max_obstruction_pct": 75.86,
    "avg_latency_ms": 26.96,
    "p95_latency_ms": 34.49,
    "avg_ping_drop_pct": 27.67,
    "probe_success_pct": 88.2,
    "clean_sample_pct": 50.22,
    "avg_download_mbps": None,
    "avg_upload_mbps": None,
}

SCORES = [
    {"use_case": "dense_urban", "label": "Dense urban broadband", "verdict": "not_suitable",
     "confidence": "high", "reason": "ping drop too high", "kpis": {}},
    {"use_case": "emergency_backup", "label": "Emergency backup internet", "verdict": "suitable",
     "confidence": "high", "reason": "meets criteria", "kpis": {}},
]

BY_SITE = pd.DataFrame([
    {"site_name": "HDB Home", "location_type": "urban_dense", "n_samples": 243,
     "avg_obstruction_pct": 71.51, "avg_ping_drop_pct": 34.73, "probe_success_pct": 92.0},
    {"site_name": "Punggol Park", "location_type": "urban_dense", "n_samples": 143,
     "avg_obstruction_pct": 2.35, "avg_ping_drop_pct": 3.07, "probe_success_pct": 90.5},
])


@pytest.fixture(autouse=True)
def _isolate_data_files(tmp_path, monkeypatch):
    monkeypatch.setattr(qa_engine, "QA_LOG_PATH", tmp_path / "qa_log.csv")
    monkeypatch.setattr(qa_engine, "MANUAL_ANSWERS_PATH", tmp_path / "manual_answers.json")
    yield


def test_is_configured_always_true():
    assert qa_engine.is_configured() is True


def test_obstruction_question_matches_rule():
    result = qa_engine.ask("What was the average obstruction?", SUMMARY, SCORES, BY_SITE)
    assert result["answered"] is True
    assert "53.97" in result["answer"]


def test_site_question_matches_specific_site():
    result = qa_engine.ask("How did Punggol Park perform?", SUMMARY, SCORES, BY_SITE)
    assert result["answered"] is True
    assert "Punggol Park" in result["answer"]
    assert "2.35" in result["answer"]


def test_use_case_question_matches_specific_verdict():
    result = qa_engine.ask("Is this suitable for emergency backup?", SUMMARY, SCORES, BY_SITE)
    assert result["answered"] is True
    assert "suitable" in result["answer"].lower()


def test_unmatched_question_is_logged_and_unanswered():
    result = qa_engine.ask("What is the meaning of life?", SUMMARY, SCORES, BY_SITE)
    assert result["answered"] is False
    pending = qa_engine.pending_questions()
    assert "What is the meaning of life?" in pending


def test_manual_answer_is_reused_and_clears_pending():
    qa_engine.ask("What is the meaning of life?", SUMMARY, SCORES, BY_SITE)
    assert "What is the meaning of life?" in qa_engine.pending_questions()

    qa_engine.save_manual_answer("What is the meaning of life?", "42")
    assert "What is the meaning of life?" not in qa_engine.pending_questions()

    result = qa_engine.ask("What is the meaning of life?", SUMMARY, SCORES, BY_SITE)
    assert result["answered"] is True
    assert result["answer"] == "42"
    assert result["source"].startswith("manual")
