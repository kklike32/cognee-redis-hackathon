# Sherlock Demo Showcase and Live Runbook

This document shows what the demo includes, how each capability works internally, and exactly how to run a live demo.

## What Is Included

- Source Intake from pasted text and uploaded files.
- Knowledge Wiki build for Deel from local markdown sources.
- Battle Card generation with citations and deal context.
- Analyst review workflow for approve, reject, and edit.
- Redis cache visibility with miss, hit, latency, and invalidation.
- Optional LLM synthesis with deterministic fallback.
- Local chunk indexing with optional Cognee ingestion.

## How It Works Internally

### 1) Source Intake

User action:
- Paste text or upload md/txt/html/htm/pdf in the Streamlit Source Intake tab.

Internal flow:
- Streamlit calls ingest_source_text or ingest_source_file.
- Extraction and normalization happen in sherlock/source_intake.py.
- New source records are written to data/sources/*.md with metadata frontmatter.

Why it matters:
- Keeps all demo source evidence local, inspectable, and replayable.

### 2) Knowledge Wiki Build

User action:
- Click Build wiki in the Knowledge Wiki tab.

Internal flow:
- build_company_wiki in sherlock/wiki_builder.py reads data/sources/*.md.
- If SHERLOCK_USE_LLM and API key are available, it attempts model synthesis.
- If that fails or is disabled, deterministic extraction path is used.
- Canonical output is written to data/wiki/deel.md.

Why it matters:
- Reliable demo baseline with optional higher-fidelity synthesis.

### 3) Battle Card Generation

User action:
- Enter deal context and click Generate brief in Battle Card tab.

Internal flow:
- generate_competitive_brief in sherlock/card_agent.py computes cache key from:
  - competitor
  - deal context
  - prompt version
  - wiki hash
  - sources hash
- Redis lookup attempts hit/miss via sherlock/cache.py.
- On miss, retrieval combines local index and optional Cognee search from sherlock/retrieval.py.
- Citations are built and a brief is generated (LLM optional, deterministic fallback always available).
- Payload is cached in Redis when cache is available.

Why it matters:
- Demonstrates practical speed-up and trustworthy cited output.

### 4) Analyst Review and Human-in-the-Loop

User action:
- Generate pending proposals, edit content, approve or reject.

Internal flow:
- generate_pending_from_wiki in sherlock/pending_generator.py compares incoming/source lines against the wiki and creates pending proposals.
- Pending queue is file-backed at data/pending/pending_changes.json.
- approve_change and reject_change in sherlock/pending_changes.py update status and timestamps.
- Approval writes approved content into data/wiki/deel.md using marked blocks.
- Approval invalidates sherlock:brief:v1:deel:* cache keys.

Why it matters:
- Demonstrates governance: AI suggestions are controlled by analyst approval.

## Streamlit App Status

Implemented entrypoint:
- app/streamlit_app.py

Tabs included:
- Source Intake
- Knowledge Wiki
- Battle Card
- Analyst Review

Sidebar helpers:
- Reset demo state
- Ingest demo data
- Environment and Redis status

## Run Instructions

1. Create and activate environment.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
```

1. Start Redis.

```bash
docker compose up -d redis
```

1. Optional environment variables.

```bash
export SHERLOCK_USE_LLM=true
export OPENAI_API_KEY=your_key_here
```

1. Reset and ingest baseline demo data.

```bash
python scripts/reset_demo.py
python scripts/ingest_demo_data.py
```

1. Start Streamlit.

```bash
streamlit run app/streamlit_app.py
```

1. Open the URL shown by Streamlit (usually <http://localhost:8501>).

## Live Demo Script (8-10 Minutes)

1. Setup Check (30-45 sec)
- Show sidebar Redis status and company scope.
- Mention local-first architecture and deterministic fallback.

1. Source Intake (1-2 min)
- Paste a short note or upload one source file.
- Click Ingest and show JSON result with saved path and content hash.

1. Knowledge Wiki (1-2 min)
- Click Build wiki.
- Call out generation mode and Cognee status.
- Scroll wiki to show evidence-backed sections.

1. Battle Card First Run (1-2 min)
- Enter deal context and click Generate brief.
- Highlight citations and cache status = miss.
- Point to latency metric.

1. Battle Card Second Run (30-60 sec)
- Click Generate brief again with same context.
- Highlight cache status = hit and reduced latency.

1. Analyst Review (2-3 min)
- Go to Analyst Review tab and Generate pending proposals.
- Open one proposal, edit wording, then Approve.
- Mention automatic cache invalidation on approval.

1. Re-Generate Brief (1 min)
- Return to Battle Card and run again.
- Show updated guidance reflected after approval.

## Troubleshooting

- If Redis is unavailable:
  - App still runs in no-cache mode (cache status disabled).
- If LLM key is missing:
  - Wiki and brief generation remain functional through deterministic fallback.
- If PDF upload fails:
  - Install pypdf or PyPDF2 in the active environment.

## Quick Validation Commands

```bash
python scripts/smoke_test.py
pytest -q
```
