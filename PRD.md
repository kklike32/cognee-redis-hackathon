PRD: Sherlock Local LLM Wiki for Competitive Intelligence
1. Product name
Sherlock
2. Product one-liner
Sherlock is a local-first LLM wiki for competitive intelligence that helps Oyster HR sales teams query fresh, cited battle cards while giving competitive analysts human-in-the-loop control over proposed updates.
3. Problem
Static competitive battle cards become stale quickly. Sales account executives need current, sourced, deal-specific guidance before calls, but competitive intelligence analysts cannot manually monitor every sales signal, competitor launch, review, and call transcript.
For a hackathon MVP, Sherlock should demonstrate the full loop:
Ingest source material.
Store knowledge in Cognee.
Cache fast responses in Redis.
Generate deal-specific sales briefs.
Show analyst-approved battle card updates.
Keep the canonical wiki as markdown.
4. Target customer
Oyster HR internal sales and competitive intelligence team
Scope:
Market: United States
Buyer segment: Seed to Series B startups
Initial competitor: Deel
Future competitors: Rippling and Remote
5. Personas
Persona A: Sales Account Executive
Needs a fast, cited brief before a competitive sales call.
Primary job:
“I have a Series A deal against Deel soon. Give me a concise brief with strengths, weaknesses, objections, talk track, and citations.”
Persona B: Competitive Intelligence Analyst
Needs to review proposed changes before anything becomes canonical.
Primary job:
“Show me what changed, why it matters, and let me approve, reject, or edit it before sales sees it.”
6. MVP scope
In scope
Local Streamlit app with two tabs:
AE View
Analyst Review
One live competitor:
Deel
Local markdown battle card:
data/wiki/deel.md
Three synthetic source documents:
Gong-style transcript
G2-style review
Product launch note
Local Cognee ingestion and retrieval
Local Redis semantic/cache layer
One Sherlock Card Agent for query answering
One handcrafted pending change
Analyst approval flow that updates the markdown card
Response citations from source docs
Visible cache hit/miss and latency
Out of scope for MVP
Cognee Cloud
Redis Cloud
Salesforce API integration
Gong API integration
G2/Capterra/TrustRadius live scraping
Multi-user auth
Slack or email delivery
Full automated Delta Agent
Full /lint implementation
Rippling and Remote live cards
Production deployment
7. Local architecture
data/sources/*.md
data/wiki/deel.md
       ↓
Local ingest script
       ↓
Cognee local knowledge graph / retrieval index
       ↓
Sherlock Card Agent
       ↓
Redis local cache
       ↓
Streamlit AE View
       ↓
Streamlit Analyst Review
       ↓
Approved update writes back to data/wiki/deel.md
8. Tech stack
Python 3.11+
Streamlit
Redis running locally through Docker
Cognee running locally
RedisVL or direct Redis client for cache/search helpers
Markdown as canonical wiki state
Local .env for model provider keys, if needed
Optional LLM provider:
Claude API
OpenAI API
Local model through Ollama or LM Studio as fallback
9. Repository structure
sherlock/
 README.md
 PRD.md
 docker-compose.yml
 pyproject.toml
 .env.example

 app/
   streamlit_app.py
   pages/
     ae_view.py
     analyst_review.py

 sherlock/
   __init__.py
   config.py
   ingest.py
   retrieval.py
   cache.py
   card_agent.py
   markdown_store.py
   pending_changes.py
   citations.py

 data/
   wiki/
     deel.md
   sources/
     gong_deel_transcript.md
     g2_deel_review.md
     deel_product_launch.md
   pending/
     pending_changes.json

 scripts/
   ingest_demo_data.py
   reset_demo.py
   smoke_test.py

 tests/
   test_cache.py
   test_markdown_store.py
   test_pending_changes.py
10. Core user flows
Flow 1: AE queries Sherlock
AE opens Streamlit app.
AE selects competitor: Deel.
AE enters deal context.
AE clicks “Generate Brief.”
Sherlock:
Reads data/wiki/deel.md
Retrieves supporting facts from Cognee
Checks Redis cache
Generates a cited sales brief
UI displays:
Recommended talk track
Strengths to acknowledge
Weaknesses to attack
Objections and responses
Source citations
Cache status
Latency
Acceptance criteria:
AE can generate a brief from the UI.
Response includes citations.
Response uses both baseline battle card and retrieved source material.
Redis cache visibly changes second-run latency/status.
App runs locally with one command after setup.
Flow 2: Analyst approves pending change
Analyst opens Analyst Review tab.
Analyst sees one pending change.
Analyst can approve, reject, or edit.
If approved:
Markdown battle card is updated.
Pending change is marked resolved.
Redis cache is invalidated.
AE reruns query and sees updated content.
Acceptance criteria:
Pending change appears in UI.
Approve updates data/wiki/deel.md.
Reject does not update markdown.
Inline edit changes the final approved text.
Cache invalidation occurs after approval.
11. Battle card markdown schema
Each competitor card should use this structure:
# Deel Battle Card

## Metadata
- Owner:
- Last reviewed:
- Confidence score:
- Pending changes:

## Positioning Headline

## Quantitative Fields
- Customer count:
- Countries served:
- Funding / valuation:
- Headcount:
- Pricing:
- Average deal size in Oyster funnel:
- Win rate vs Deel last 90 days:

## Strengths to Acknowledge

## Weaknesses to Attack

## Common Objections and Responses

## Trap-Setting Discovery Questions

## Customer Evidence

## Segment-Specific Talk Track

## Recent Activity

## Sources
12. Demo script
0:00 to 0:20
Static battle cards go stale. Sherlock keeps them fresh by combining Cognee retrieval, Redis caching, and analyst approval.
0:20 to 1:05
Open AE View. Select Deel. Enter:
Series A fintech startup, 80 employees, expanding into Canada and the UK, currently evaluating Deel.
Generate brief. Show cited output and cache latency.
1:05 to 1:50
Open Analyst Review. Show pending change from synthetic source. Approve it.
1:50 to 2:30
Return to AE View. Rerun the same query. Show updated battle card content and cache invalidation.
2:30 to 3:00
Explain architecture:
Markdown wiki is canonical. Cognee provides structured retrieval. Redis handles local cache and fast state. Analyst approval prevents untrusted automatic edits.

