# Sherlock

Sherlock is a local-first LLM wiki for competitive intelligence. The demo helps Oyster HR account executives generate cited battle-card briefs against Deel while a competitive intelligence analyst reviews proposed changes before they update the canonical markdown wiki.

Everything runs locally:

- Redis Stack via Docker Compose
- Local Cognee package when installed, with a deterministic local fallback
- Canonical battle card state in `data/wiki/deel.md`
- Synthetic source docs in `data/sources`
- Streamlit UI for AE and analyst workflows

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[cognee]"
cp .env.example .env
docker compose up -d redis
```

If Cognee install time is a concern, the demo still runs with:

```bash
python3 -m pip install -e .
```

The default `.env.example` sets `MOCK_EMBEDDING=true` and `COGNEE_SKIP_COGNIFY=true` so the demo is reliable without an LLM key. Add `OPENAI_API_KEY` or `LLM_API_KEY` only if you want to experiment with real local Cognee cognify behavior.

## Run The Demo

```bash
python3 scripts/reset_demo.py
python3 scripts/ingest_demo_data.py
streamlit run app/streamlit_app.py
```

Open the Streamlit URL, then:

1. In AE View, keep competitor `Deel`.
2. Use the default context: Series A fintech, 80 employees, expanding into Canada and the UK.
3. Generate a brief and note citations, cache status, and latency.
4. Generate the same brief again to show a Redis cache hit.
5. In Analyst Review, approve or edit the pending change.
6. Return to AE View and regenerate to show the updated wiki content and cache invalidation.

## Smoke Test

With Redis running:

```bash
python3 scripts/smoke_test.py
```

The smoke test verifies Redis connectivity, Streamlit imports, local ingestion, cited brief generation, Redis cache hit behavior, approval-based markdown mutation, and cache invalidation. It resets the demo state when it finishes.

## Project Layout

```text
app/streamlit_app.py           Streamlit AE and analyst UI
sherlock/config.py             Local settings and paths
sherlock/ingest.py             Demo markdown ingestion with Cognee attempt
sherlock/retrieval.py          Deterministic local retrieval fallback
sherlock/cache.py              Redis response cache and invalidation
sherlock/card_agent.py         Sherlock competitive brief generator
sherlock/markdown_store.py     Canonical markdown update helpers
sherlock/pending_changes.py    Analyst approval workflow
sherlock/citations.py          Stable source citation formatting
data/wiki/deel.md              Canonical battle card
data/sources/*.md              Synthetic source evidence
data/pending/*.json            Pending analyst changes
scripts/reset_demo.py          Restore demo state
scripts/ingest_demo_data.py    Ingest local demo docs
scripts/smoke_test.py          End-to-end smoke checks
```

## Notes

- Sherlock does not use Cognee Cloud or Redis Cloud.
- Redis is used for local response caching. Ingestion also writes a local chunk index under `.cache/sherlock_chunks.json` for deterministic demo retrieval.
- Cognee is attempted locally if installed. If Cognee or an LLM key is missing, the app keeps working with deterministic retrieval and brief generation.
- The MVP supports Deel only.
