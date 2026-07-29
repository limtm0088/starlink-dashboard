"""Rule-based (non-LLM) Q&A. No API key, no network call, cannot hallucinate:
every answer is either a previously-approved manual answer or a template
built directly from this dataset's real KPI/use-case numbers.

Matching order for each question:
    1. data/manual_answers.json -- answers the technical director has
       already approved for a close/identical past question.
    2. Keyword-matched topics (obstruction, ping drop, latency, use-case
       verdicts, site-type confound, etc.) -- answer built from the live
       kpi_summary / use_case_scores / by_site data passed in.
    3. No match -- logged to data/qa_log.csv with answered=False so the
       technical director can review and answer it later via the "Answer
       pending questions" panel in the AI Q&A tab. Once answered there, it
       moves to manual_answers.json and step 1 will catch it next time.
"""
from __future__ import annotations

import csv
import difflib
import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
KB_PATH = DATA_DIR / "knowledge_base.json"
QA_LOG_PATH = DATA_DIR / "qa_log.csv"
MANUAL_ANSWERS_PATH = DATA_DIR / "manual_answers.json"

_MANUAL_MATCH_CUTOFF = 0.75  # difflib ratio threshold for "close enough" match


def is_configured() -> bool:
    """Always true -- the rule-based matcher needs no external config."""
    return True


# ---------------------------------------------------------------------------
# Logging + manual answers
# ---------------------------------------------------------------------------

def _log_question(question: str, answer: str, answered: bool, source: str) -> None:
    is_new = not QA_LOG_PATH.exists()
    with QA_LOG_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp", "question", "answer", "answered", "source"])
        writer.writerow([datetime.now(timezone.utc).isoformat(), question, answer, answered, source])


def load_past_log() -> list[dict]:
    if not QA_LOG_PATH.exists():
        return []
    with QA_LOG_PATH.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_manual_answers() -> list[dict]:
    if not MANUAL_ANSWERS_PATH.exists():
        return []
    with MANUAL_ANSWERS_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def save_manual_answer(question: str, answer: str) -> None:
    entries = load_manual_answers()
    entries.append({
        "question": question,
        "answer": answer,
        "answered_at": datetime.now(timezone.utc).isoformat(),
    })
    with MANUAL_ANSWERS_PATH.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def _match_manual(question: str) -> dict | None:
    entries = load_manual_answers()
    if not entries:
        return None
    q_norm = question.strip().lower()
    best, best_ratio = None, 0.0
    for entry in entries:
        ratio = difflib.SequenceMatcher(None, q_norm, entry["question"].strip().lower()).ratio()
        if ratio > best_ratio:
            best, best_ratio = entry, ratio
    if best and best_ratio >= _MANUAL_MATCH_CUTOFF:
        return best
    return None


def pending_questions() -> list[str]:
    """Logged questions that are still unanswered and have no manual answer yet."""
    manual_qs = [e["question"].strip().lower() for e in load_manual_answers()]
    seen: dict[str, None] = {}
    for row in load_past_log():
        if row.get("answered") == "False":
            q = row["question"]
            q_norm = q.strip().lower()
            already_answered = any(
                difflib.SequenceMatcher(None, q_norm, m).ratio() >= _MANUAL_MATCH_CUTOFF
                for m in manual_qs
            )
            if not already_answered:
                seen[q] = None
    return list(seen.keys())


# ---------------------------------------------------------------------------
# Topic matching against live data
# ---------------------------------------------------------------------------

def _fmt(v) -> str:
    return "n/a" if v is None else str(v)


def _topic_obstruction(q, kpi_summary, use_case_scores, by_site, kb) -> str:
    return (
        f"Average obstruction across the filtered data is {_fmt(kpi_summary.get('avg_obstruction_pct'))}%, "
        f"with a maximum of {_fmt(kpi_summary.get('max_obstruction_pct'))}%."
    )


def _topic_ping_drop(q, kpi_summary, use_case_scores, by_site, kb) -> str:
    return f"Average Starlink POP ping drop is {_fmt(kpi_summary.get('avg_ping_drop_pct'))}%."


def _topic_latency(q, kpi_summary, use_case_scores, by_site, kb) -> str:
    return (
        f"Average Starlink POP latency is {_fmt(kpi_summary.get('avg_latency_ms'))}ms, "
        f"p95 is {_fmt(kpi_summary.get('p95_latency_ms'))}ms."
    )


def _topic_probe_success(q, kpi_summary, use_case_scores, by_site, kb) -> str:
    return (
        f"Combined external probe success (DNS/HTTP/TCP-443/small-download) is "
        f"{_fmt(kpi_summary.get('probe_success_pct'))}%, with {_fmt(kpi_summary.get('clean_sample_pct'))}% "
        f"of samples fully clean (all probes succeeded and zero ping drop)."
    )


def _topic_throughput(q, kpi_summary, use_case_scores, by_site, kb) -> str:
    return (
        "No download/upload figure is reported: the source rig has never run a real speedtest. "
        "The raw downlink/uplink telemetry it does have is idle link-utilization data, not throughput "
        "capacity, so it's kept out of the headline KPIs (see Methodology tab)."
    )


def _topic_samples(q, kpi_summary, use_case_scores, by_site, kb) -> str:
    return f"{kpi_summary.get('n_samples')} samples are in the currently filtered dataset."


def _topic_confound(q, kpi_summary, use_case_scores, by_site, kb) -> str:
    return kb.get("site_type_confound", {}).get("summary", "No entry found.")


def _topic_regulatory(q, kpi_summary, use_case_scores, by_site, kb) -> str:
    return kb.get("imda_regulatory_gap", {}).get("summary", "No entry found.")


def _topic_vendor(q, kpi_summary, use_case_scores, by_site, kb) -> str:
    return kb.get("starlink_vendor_spec", {}).get("summary", "No entry found.")


def _topic_standards(q, kpi_summary, use_case_scores, by_site, kb) -> str:
    parts = [kb[k]["summary"] for k in ("3gpp_ntn_latency", "itu_t_y1541_class0") if k in kb]
    return " ".join(parts) or "No entry found."


def _topic_use_case(q, kpi_summary, use_case_scores, by_site, kb) -> str:
    q_lower = q.lower()
    for r in use_case_scores:
        if r["use_case"].replace("_", " ") in q_lower or r["label"].lower() in q_lower:
            return f"{r['label']}: {r['verdict']} ({r['confidence']} confidence) — {r['reason']}"
    lines = [f"{r['label']}: {r['verdict']} ({r['confidence']} confidence)" for r in use_case_scores]
    return "Use-case verdicts — " + "; ".join(lines)


def _topic_site(q, kpi_summary, use_case_scores, by_site, kb) -> str | None:
    q_lower = q.lower()
    if by_site is None or by_site.empty:
        return None
    for _, row in by_site.iterrows():
        site_lower = row["site_name"].lower()
        site_keywords = site_lower.split() + [site_lower]
        if any(kw in q_lower for kw in site_keywords if len(kw) > 2):
            return (
                f"{row['site_name']}: {row['n_samples']} samples, avg obstruction "
                f"{_fmt(row.get('avg_obstruction_pct'))}%, avg ping drop {_fmt(row.get('avg_ping_drop_pct'))}%, "
                f"probe success {_fmt(row.get('probe_success_pct'))}%."
            )
    return None


# keyword -> (builder, weight). First topic whose keywords best-match the
# question (most keyword hits) wins.
_TOPICS = [
    (["obstruction", "sky view", "blocked"], _topic_obstruction),
    (["ping drop", "packet loss", "packet drop", "drop rate"], _topic_ping_drop),
    (["latency", "ping ms", "delay"], _topic_latency),
    (["probe success", "availability", "uptime", "reliable", "reliability", "clean sample"], _topic_probe_success),
    (["download", "upload", "throughput", "speed", "bandwidth", "speedtest", "mbps"], _topic_throughput),
    (["how many sample", "sample size", "data point", "number of samples"], _topic_samples),
    (["confound", "bias", "site type", "evidence gap", "confidence", "flaw"], _topic_confound),
    (["regulatory", "imda standard", "compliance", "official limit", "regulation"], _topic_regulatory),
    (["vendor", "starlink spec", "starlink claim", "official spec"], _topic_vendor),
    (["3gpp", "itu", "ntn", "standard", "y.1541", "y1541"], _topic_standards),
    (["verdict", "suitable", "use case", "recommend", "dense urban", "emergency", "maritime",
      "remote worksite", "critical infra", "video call", "vpn", "gaming", "cctv"], _topic_use_case),
]


def ask(question: str, kpi_summary: dict, use_case_scores: list[dict], by_site=None) -> dict:
    manual = _match_manual(question)
    if manual is not None:
        return {"answer": manual["answer"], "answered": True, "source": "manual (technical director)"}

    with KB_PATH.open(encoding="utf-8") as f:
        kb = json.load(f)

    q_lower = question.lower()

    site_answer = _topic_site(question, kpi_summary, use_case_scores, by_site, kb)
    if site_answer is not None:
        _log_question(question, site_answer, True, "rule:site")
        return {"answer": site_answer, "answered": True, "source": "rule-matched (site)"}

    best_topic, best_score = None, 0
    for keywords, builder in _TOPICS:
        score = sum(1 for kw in keywords if kw in q_lower)
        if score > best_score:
            best_topic, best_score = builder, score

    if best_topic is not None:
        answer = best_topic(question, kpi_summary, use_case_scores, by_site, kb)
        _log_question(question, answer, True, f"rule:{best_topic.__name__}")
        return {"answer": answer, "answered": True, "source": "rule-matched"}

    fallback = "No matching info in the current data/knowledge base. Logged for the technical director to answer."
    _log_question(question, fallback, False, "unmatched")
    return {"answer": fallback, "answered": False, "source": None}
