# Sherlock

Sherlock is a local-first, Oyster-internal competitive intelligence demo for one competitor: Deel.

It shows three layers:

1. **Raw Source Intake**: upload or paste internal source material into `data/sources/`.
2. **Knowledge Wiki**: build `data/wiki/deel.md` from cited local sources with optional LLM synthesis and deterministic fallback.
3. **Battle Card Agent**: generate a deal-specific, cited AE brief with Redis cache hit/miss, local retrieval, and analyst-approved cache invalidation.

No Cognee Cloud, Redis Cloud, CRM, Gong, G2, Slack, or live web search integrations are used.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[cognee]"
cp .env.example .env
docker compose up -d redis
```

If Cognee install time is a concern, the demo still works with:

```bash
python3 -m pip install -e .
```

The reliable demo path does not require an LLM key. If `SHERLOCK_USE_LLM=true` and `OPENAI_API_KEY` or `LLM_API_KEY` is set, Sherlock will try LLM wiki/brief synthesis and fall back to deterministic generation on failure.

## Run The Demo

```bash
python3 scripts/reset_demo.py
python3 scripts/ingest_demo_data.py
python3 scripts/smoke_test.py
streamlit run app/streamlit_app.py
```

Streamlit tabs:

- `1. Source Intake`: paste or upload `.md`, `.txt`, `.html`, `.htm`, or `.pdf` files. PDF requires `pypdf` or `PyPDF2`; otherwise Sherlock returns a clear unsupported parser error.
- `2. Knowledge Wiki`: build the Deel wiki, refresh local chunks, show Redis/Cognee status, and preview `data/wiki/deel.md`.
- `3. Battle Card`: generate the AE-ready cited brief. First run should show Redis `miss`; the second identical run should show `hit` when Redis is available.
- `Analyst Review`: approve, reject, or edit pending changes. Approval writes to `data/wiki/deel.md` and invalidates cached Deel briefs.

Demo query:

```text
Series A fintech startup with 80 employees, expanding into Canada and the UK, currently evaluating Deel. They care about onboarding speed, compliance confidence, and predictable pricing.
```

## Public APIs

```python
from sherlock.source_intake import ingest_source_text, ingest_source_file
from sherlock.wiki_builder import build_company_wiki
from sherlock.card_agent import generate_competitive_brief

ingest_source_text("Deel call note", "Buyer asked about compliance support.", "gong-style source")
build_company_wiki(company="deel", use_llm=True)
generate_competitive_brief(competitor="deel", deal_context="Series A fintech...")
```

`generate_competitive_brief` returns `brief_markdown`, `sources`, `cache_status`, `latency_ms`, `model_used`, and retrieval status. `build_company_wiki` returns `wiki_markdown`, `sources`, `generation_mode`, `cognee_status`, and `latency_ms`.

## Local Architecture

```text
data/sources/*.md
  -> source intake + ingest_demo_data
  -> .cache/sherlock_chunks.json deterministic local index
  -> optional local Cognee add/cognify/search
  -> data/wiki/deel.md knowledge wiki
  -> Sherlock Card Agent
  -> local Redis response cache
  -> Streamlit AE brief
  -> analyst approval updates wiki and invalidates sherlock:brief:v1:deel:*
```

Redis is the reliable local cache/status layer. Cognee is optional local knowledge indexing/search and reports `indexed`, `added_not_cognified`, `missing`, or `error`.

The older `src/app` package contains supporting local Redis/Cognee helper code from the scaffold. The active Sherlock demo path is the root `sherlock/` package plus `app/streamlit_app.py`.

## Test Commands

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/smoke_test.py
REDIS_URL=redis://localhost:1/0 .venv/bin/python scripts/smoke_test.py
```

The smoke test validates source-backed wiki build, local chunk ingestion, cited retrieval, cited brief generation, Redis `miss` then `hit` when available, no-cache fallback when Redis is unavailable, analyst approval, cache invalidation, and regenerated brief freshness.

## Constraints

- Deel only.
- Oyster internal only.
- Upload and paste source intake only; no live URL fetching or LLM web search.
- All durable demo state is local markdown/JSON plus local Redis cache.
- Deterministic fallback is required and is the default for live demo reliability.
