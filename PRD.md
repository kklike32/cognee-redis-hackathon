# PRD: Sherlock Local Competitive Intelligence Wiki

## Product

Sherlock is a local-first LLM wiki for competitive intelligence. For the hackathon MVP, it helps Oyster HR sales account executives query fresh, cited battle cards against Deel while a competitive intelligence analyst reviews and approves proposed changes before they update the canonical markdown wiki.

## Goals

- Demonstrate a complete loop from raw source intake to knowledge-wiki build to cited sales brief to analyst-approved wiki update.
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
uploaded/pasted internal sources
  -> data/sources/*.md
  -> deterministic or optional-LLM knowledge wiki build
  -> data/wiki/deel.md
  -> local Cognee attempt + deterministic local chunk index
  -> Sherlock Card Agent
  -> local Redis response cache
  -> Streamlit Battle Card view
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

1. AE opens `3. Battle Card`.
2. AE enters deal context for the Deel opportunity.
3. Sherlock builds a cache key from competitor, deal context, wiki hash, source hash, and prompt version.
4. On Redis hit, Sherlock returns cached brief and latency.
5. On miss, Sherlock retrieves local evidence, formats citations, generates a deterministic competitive brief, and stores it in Redis.
6. UI shows brief, citations, cache status, latency, and retrieval status.

## User Flow: Source Intake And Knowledge Wiki

1. Analyst opens `1. Source Intake`.
2. Analyst uploads `.md`, `.txt`, `.html`, `.htm`, or supported `.pdf` files, or pastes source text.
3. Sherlock saves normalized local markdown records under `data/sources/`.
4. Analyst opens `2. Knowledge Wiki` and builds the Deel wiki.
5. Sherlock uses optional LLM synthesis only when explicitly enabled and otherwise uses deterministic extractive synthesis.
6. Wiki build refreshes the local chunk index and invalidates cached Deel briefs.

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
5. In `1. Source Intake`, optionally add a pasted internal source.
6. In `2. Knowledge Wiki`, build the Deel wiki.
7. In `3. Battle Card`, generate a Deel brief for the Series A fintech context.
8. Generate again to show cache hit.
9. In Analyst Review, approve the compliance ownership change.
10. Return to Battle Card and regenerate to show updated battle-card guidance and cache invalidation.

## Acceptance Criteria

- `docker compose up -d redis` starts local Redis.
- `python3 scripts/ingest_demo_data.py` ingests local markdown source docs.
- Source Intake saves normalized local markdown records under `data/sources/`.
- Knowledge Wiki builds `data/wiki/deel.md` from local cited source docs.
- `streamlit run app/streamlit_app.py` starts the demo.
- Battle Card generates a competitive brief for Deel.
- Brief includes citations and uses deal context.
- UI shows cache hit/miss and latency.
- Analyst Review shows a pending change.
- Analyst can approve, reject, or edit.
- Approving updates `data/wiki/deel.md`.
- Approving invalidates relevant Redis cache keys.
- Reset script restores demo state.
- Smoke test validates the full loop.

## Known Limitations

- Deterministic fallback is the default for demo reliability; optional LLM synthesis is gated by env and API key.
- Cognee is optional at runtime; missing package or missing LLM key does not block the demo.
- The pending-change queue is file-backed JSON.
- Markdown updates are section-targeted and intentionally simple.
