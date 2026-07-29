# Starlink Mini — IMDA Evidence Dashboard

Streamlit dashboard presenting Starlink Mini Kit field-test data as evidence
for IMDA on whether LEO satellite broadband is technically useful in
Singapore (dense urban, maritime, remote worksite, critical infrastructure
backup, emergency backup).

## Setup

```bash
pip install -r requirements.txt
```

## Data

Real field data lives in this repo's `data/real_starlink_obstruction_test_data.csv`,
generated from the source monitoring rig at
`../starlink monitoring system/data/obstruction-tests/`. If new test
sessions are added there, re-run:

```bash
python data/convert_real_obstruction_data.py
```

To regenerate the synthetic sample dataset (for exploring the dashboard
without real data):

```bash
python data/generate_sample_data.py
```

## Run

```bash
streamlit run app.py
```

Opens on real field data by default (sidebar lets you switch to the
synthetic sample or upload your own CSV matching `config/schema.py`).

## Layout

- `app.py` — 6-tab Streamlit UI (see its module docstring for exactly what's in each tab).
- `config/schema.py` — the CSV data contract every dataset must satisfy.
- `config/thresholds.py` — every comparison baseline, tagged by `source_type`
  (measured / vendor_spec / standards_reference / regulatory_reference /
  assumption) so a measured finding is never visually conflated with an
  external reference.
- `config/use_cases.py` — the 5 candidate IMDA use cases and their
  engineering acceptance criteria.
- `core/ingest.py` — schema validation.
- `core/metrics.py` — KPI aggregation (measured values only).
- `core/scoring.py` — explainable use-case scoring rubric; returns
  `insufficient_data` rather than a guess when a use case has no matching
  `location_type` in the loaded dataset.
- `core/qa_engine.py` — rule-based (no API key, no network call) Q&A: keyword-matches
  a question against `data/knowledge_base.json` and the live KPI/use-case data, or
  a previously-approved answer in `data/manual_answers.json`. Unmatched questions are
  logged to `data/qa_log.csv` for the technical director to answer via the AI Q&A
  tab's "Answer pending questions" panel — once answered, they're reused automatically.

## Known evidence gap

The 3 real sites (HDB home, MBC office, Punggol Park) differ in both
obstruction level and site type — this dataset cannot yet separate "siting
technique reduces obstruction" from "an open park has less obstruction than
a building." See the **Risks & Limitations** tab. The recommended next test
is 2-3 placements within the same building before any pilot/policy
recommendation.
