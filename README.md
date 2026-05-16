# FounderOS Memory Wiki

Hackathon-ready Python scaffold for an AI memory/wiki system powered by local Cognee and Redis.

The project is backend-first and intentionally small. It gives you a working path for:

- ingesting markdown notes into Cognee
- optionally indexing the same content in Redis with RedisVL
- retrieving LLM-ready context chunks
- routing that context through lightweight GTM research agents

## Architecture

```text
User notes/docs
→ ingestion pipeline
→ Cognee knowledge graph / memory
→ Redis vector/cache layer
→ retrieval layer
→ specialized GTM agents
→ structured recommendations
```

The first version keeps the Cognee integration isolated behind a thin wrapper so the local SDK and adapter details can be patched later without touching the rest of the app.

The scaffold also writes a small local cache under `.cache/knowledge_chunks.json` so you can still demo retrieval behavior while Redis or Cognee credentials are being wired up.

## Project Layout

```text
project-root/
  README.md
  .env.example
  .gitignore
  pyproject.toml
  src/
    app/
      __init__.py
      config.py
      redis_client.py
      cognee_client.py
      openai_client.py
      local_store.py
      ingest.py
      retrieve.py
      main.py
      agents/
        __init__.py
        base.py
        gtm_research_agent.py
        competitor_agent.py
        customer_agent.py
        pricing_agent.py
  scripts/
    check_redis.py
    check_cognee.py
    check_openai.py
    ingest_sample.py
    query_sample.py
  data/
    sample_gtm_notes.md
  tests/
    test_config.py
```

## Setup

1. Create a virtual environment.
2. Install the project in editable mode.

```bash
pip install -e .
```

If you want the local Cognee SDK integration, install the optional extra:

```bash
pip install -e ".[cognee]"
```

3. Copy `.env.example` to `.env` and fill in your credentials.

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

## Example Flow

1. Ingest the sample markdown notes.
2. Query for customer pain points, ICP, competitors, or pricing.
3. Route the retrieved context through a specialized agent.
4. Use the returned structured dictionary as the basis for a future LLM prompt.

## Extension Ideas

- Add a real embedding provider in `embed_text()`.
- Replace the Cognee wrapper with direct SDK calls once you finalize the local provider stack.
- Add more GTM agents for positioning, messaging, SEO, or sales enablement.
- Add a FastAPI layer if you want this to power a web demo.
- Add richer chunking, document types, and metadata filters.

## Known TODOs

- Confirm the exact local Cognee SDK methods you want to standardize on for your demo.
- Swap the deterministic placeholder embeddings for OpenAI, Cohere, or another provider.
- Decide whether you want RedisVL to be the sole retrieval layer or just a cache/vector supplement.
- Add persistence, auth, and background jobs if this turns into a longer-lived service.
