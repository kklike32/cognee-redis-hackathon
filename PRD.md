# PRD: Sherlock Local Competitive Intelligence Wiki

## Product

Sherlock is a local-first LLM wiki for competitive intelligence. For the hackathon MVP, it helps Oyster HR sales account executives query fresh, cited battle cards against Deel while a competitive intelligence analyst reviews and approves proposed changes before they update the canonical markdown wiki.

## Goals

- Demonstrate a complete loop from source ingestion to cited sales brief to analyst-approved wiki update.
- Keep all state local and inspectable.
- Optimize for demo reliability over production architecture.
- Show Redis value through visible cache hit/miss, latency, and invalidation after approval.
- Show Cognee value through a local ingestion/retrieval path when the local package is installed, with graceful fallback.

## Non-Goals

- No Cognee Cloud.
- No Redis Cloud.
- No Salesforce, Gong, G2, Slack, email, or external production API integrations.
- No multi-user auth.
- No production deployment.
- No multi-competitor support beyond Deel.

## Personas

**Account Executive**

Needs a concise, deal-specific competitive brief with citations before a sales call.

**Competitive Intelligence Analyst**

Needs to review proposed battle-card changes and approve, reject, or edit them before they become canonical.

## Architecture

```text
data/sources/*.md + data/wiki/deel.md
  -> scripts/ingest_demo_data.py
  -> local Cognee attempt + deterministic local chunk index
  -> Sherlock Card Agent
  -> local Redis response cache
  -> Streamlit AE View
  -> Streamlit Analyst Review
  -> approved update writes to data/wiki/deel.md
  -> Redis cache invalidation
```

Canonical state lives in markdown:

- `data/wiki/deel.md`
- `data/sources/gong_deel_transcript.md`
- `data/sources/g2_deel_review.md`
- `data/sources/deel_product_launch.md`
- `data/pending/pending_changes.json`

## User Flow: AE View

1. AE selects Deel.
2. AE enters deal context.
3. Sherlock builds a cache key from competitor, deal context, wiki hash, source hash, and prompt version.
4. On Redis hit, Sherlock returns cached brief and latency.
5. On miss, Sherlock retrieves local evidence, formats citations, generates a deterministic competitive brief, and stores it in Redis.
6. UI shows brief, citations, cache status, latency, and retrieval status.

## User Flow: Analyst Review

1. Analyst opens pending change.
2. Analyst can edit proposed markdown.
3. Analyst approves or rejects.
4. Approval inserts a marked block into the target section of `data/wiki/deel.md`.
5. Approval marks the pending change approved and invalidates `sherlock:brief:v1:deel:*` Redis keys.
6. Reset script removes approved blocks and restores the pending queue for repeated demos.

## Demo Script

1. Start Redis locally with `docker compose up -d redis`.
2. Run `python3 scripts/reset_demo.py`.
3. Run `python3 scripts/ingest_demo_data.py`.
4. Run `streamlit run app/streamlit_app.py`.
5. In AE View, generate a Deel brief for the Series A fintech context.
6. Generate again to show cache hit.
7. In Analyst Review, approve the compliance ownership change.
8. Return to AE View and regenerate to show updated battle-card guidance and cache invalidation.

## Acceptance Criteria

- `docker compose up -d redis` starts local Redis.
- `python3 scripts/ingest_demo_data.py` ingests local markdown source docs.
- `streamlit run app/streamlit_app.py` starts the demo.
- AE View generates a competitive brief for Deel.
- Brief includes citations and uses deal context.
- UI shows cache hit/miss and latency.
- Analyst Review shows a pending change.
- Analyst can approve, reject, or edit.
- Approving updates `data/wiki/deel.md`.
- Approving invalidates relevant Redis cache keys.
- Reset script restores demo state.
- Smoke test validates the full loop.

## Known Limitations

- The LLM response is deterministic for demo reliability.
- Cognee is optional at runtime; missing package or missing LLM key does not block the demo.
- The pending-change queue is file-backed JSON.
- Markdown updates are section-targeted and intentionally simple.
