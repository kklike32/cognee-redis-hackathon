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

## Environment Variables

Required / supported:

- `REDIS_URL`
- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_USERNAME`
- `REDIS_PASSWORD`
- `REDIS_SSL`
- `REDIS_ACCOUNT_KEY`
- `REDIS_API_KEY`
- `ENABLE_BACKEND_ACCESS_CONTROL`
- `MOCK_EMBEDDING`
- `COGNEE_SKIP_COGNIFY`
- `COGNEE_DATASET_NAME`
- `LLM_PROVIDER`
- `LLM_MODEL`
- `LLM_ENDPOINT`
- `LLM_API_KEY`
- `EMBEDDING_PROVIDER`
- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSIONS`
- `EMBEDDING_ENDPOINT`
- `EMBEDDING_API_KEY`
- `VECTOR_DB_PROVIDER`
- `VECTOR_DB_URL`
- `VECTOR_DB_KEY`
- `CACHING`
- `CACHE_BACKEND`
- `OPENAI_API_KEY`
- `APP_ENV`

Redis can be configured either with `REDIS_URL` or the host/port/username/password fields.

`REDIS_ACCOUNT_KEY` and `REDIS_API_KEY` are Redis Cloud REST API credentials. They are useful for management/API workflows, but this scaffold's Redis client still needs a database connection URI or host/port/user/password for runtime access.

## Redis Setup Notes

1. For the hackathon demo, run Redis locally with Docker or a local Redis install.
2. Use `REDIS_HOST=localhost`, `REDIS_PORT=6379`, and `REDIS_SSL=false` for the default local setup.
3. If you want Redis Cloud later, set `REDIS_URL` or the split connection fields and flip `REDIS_SSL=true` only when you are using TLS.
4. `REDIS_ACCOUNT_KEY` and `REDIS_API_KEY` are still only Redis Cloud REST API credentials; they are not needed for the local demo.
5. A quick local Redis start command is:

```bash
docker run -d --name redis -p 6379:6379 redis:8.0.2
```

RedisVL uses a vector schema for knowledge chunks. The demo uses deterministic placeholder embeddings for the app's own Redis index, while local Cognee uses the configured embedding provider.

## Cognee Local Setup Notes

1. Install Cognee plus the Redis vector adapter: `pip install -e ".[cognee]"`
2. Run Redis locally. The default config uses `VECTOR_DB_PROVIDER=redis` and `VECTOR_DB_URL=redis://localhost:6379`.
3. Leave `ENABLE_BACKEND_ACCESS_CONTROL=false` for the local Redis demo. Cognee checks this flag from process environment variables, so the app loads `.env` into `os.environ` before the SDK is used.
4. Configure both the LLM and embedding provider together. The sample `.env` uses OpenAI for both so the same API key can power the local Cognee runtime.
5. Before the first local run after changing providers, prune old Cognee state if needed. The Cognee docs recommend `cognee.prune.prune_system(metadata=True)` when switching embedding/vector providers.
6. If outbound OpenAI calls are not available in your environment, set `MOCK_EMBEDDING=true` and `COGNEE_SKIP_COGNIFY=true` for a demo-only local path that still ingests into Redis and returns chunk search results.

The Cognee wrapper is intentionally isolated and marked so the SDK/config details can be tuned without touching the rest of the app.

## Run Commands

All commands assume the project has been installed with `pip install -e .`.

```bash
python -m app.main check-redis
python -m app.main check-cognee
python -m app.main check-openai
python -m app.main ingest data/sample_gtm_notes.md
python -m app.main query "Who is our ICP?"
python -m app.main agent gtm "What GTM wedge should we start with?"
```

Scripts are also available:

```bash
python scripts/check_redis.py
python scripts/check_cognee.py
python scripts/check_openai.py
python scripts/ingest_sample.py
python scripts/query_sample.py
```

## Local Demo UI

Run the Sherlock demo UI locally without Streamlit:

```bash
python app/local_web_app.py
```

Then open `http://127.0.0.1:8765`.

The UI has four views:

- AE View: select `Deel`, enter deal context, and generate a deterministic cited brief.
- Wiki Intake: convert local incoming/source markdown into pending analyst proposals.
- Analyst Review: approve, reject, or edit pending changes from `data/pending/pending_changes.json`.
- Battle Card: inspect the canonical local markdown in `data/wiki/deel.md`.

Approval appends the final text to `data/wiki/deel.md` under `## Recent Analyst-Approved Updates` and invalidates the local Redis cache prefix for Deel. Rejection only marks the pending change rejected. Wiki Intake reads from `data/incoming/` and `data/sources/`, compares those local files to the current battle card, and writes proposed changes to pending.

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
