# Sources Roadmap — Inputs to the LLM Wiki

This document tracks what we currently ingest, what we should add next, and what is on the long-term wishlist. Owner: Competitive Intelligence team.

---

## Currently ingested (Tier 1, in the demo)

| Source | Format | Frequency | What it updates |
|---|---|---|---|
| Gong call transcripts | Markdown (synthetic) | Continuous | Wiki strengths/weaknesses, recent objections, win/loss patterns |
| G2 / Capterra reviews | Markdown (synthetic) | Weekly | Wiki general strengths/weaknesses, sentiment shifts |
| Competitor product launches | Markdown (scraped + synthetic) | As released | Wiki recent activity, growth signals, emerging strengths |
| Salesforce won/lost reports | Markdown table | Monthly | Wiki win rates, top loss reasons, deal pattern detection |

---

## High priority to add next (Tier 2, next 30 days)

| Source | What it tells us | How to ingest |
|---|---|---|
| **LinkedIn hiring + headcount changes** | Where competitor is investing (product, eng, GTM by region) | Scrape via Talentscan, Pinpoint, or competitor careers page weekly |
| **Job postings (BuiltIn, AngelList, competitor careers pages)** | What skills they hire for = product roadmap signal | Weekly scrape, RSS feeds where available |
| **Press releases and funding news** | Investor profile, valuation, strategic direction | Crunchbase News, TechCrunch, PitchBook API |
| **Competitor blog posts and changelogs** | Product announcements, positioning shifts, customer stories | RSS feed subscription per competitor |
| **Analyst reports (Gartner Magic Quadrant, Forrester Wave)** | Market positioning, third party validation | Annual or quarterly, manual upload |
| **Pricing page changes over time** | Price moves, plan restructuring | Daily scrape with diff detection |

---

## Medium priority (Tier 3, next 60 to 90 days)

| Source | What it tells us | How to ingest |
|---|---|---|
| Twitter / X posts from competitor leadership | Positioning soundbites, hiring announcements, product hints | Weekly scrape via API |
| Conference talks and podcast appearances | Strategic direction, target ICP, leadership tone | Manual + transcript service (Otter, Rev) |
| Integration partner announcements | Ecosystem play, channel strategy | Subscribe to competitor partner pages |
| YouTube product demos and webinars | Product capability evidence (vs marketing claims) | Manual upload + transcript |
| Customer support ticket trends (where visible publicly) | Where competitors fail at scale | Aggregate from public reviews + community forums |

---

## Internal sources (high value, requires process change)

| Source | What it tells us | Required process |
|---|---|---|
| **Lost deal post-mortems** | Deeper than CRM reason codes (the actual story of why we lost) | AE writes 200 word post-mortem within 48 hours of loss |
| **CSM observed objection patterns** | New objections surfacing in customer expansion conversations | Monthly CSM debrief, tagged in Notion |
| **Win story interviews with CSMs** | Why we won, what the customer's specific compliance need was | Quarterly customer reference call audio |
| **Customer reference calls (where competitor was discussed)** | Real-time competitive intel from current customers | Tag reference calls in Gong with "competitive" |

---

## Long tail / quirky (Tier 4, opportunistic)

| Source | What it tells us |
|---|---|
| Anonymous review sites (Blind, RepVue) | Internal sentiment at competitor, retention signals |
| Reddit r/EOR, r/sales, procurement Slack groups | Buyer chatter, real time market sentiment |
| Sales engineer demos posted publicly (YouTube) | Product capability ground truth vs marketing |
| Internal RFP responses from competitors (when prospects share) | Pricing + positioning playbook from competitor SE team |
| Hiring videos / day in the life from competitor employees | Cultural positioning, internal narrative |
| Glassdoor reviews of competitor | Internal health, attrition risk, where they're rebuilding |

---

## Source design principles

1. **Every source must produce structured output for the agent.** Free-text dumps are useless. We extract entities, claims, and citations.
2. **Every claim must cite its source.** No claim makes it into the wiki without provenance.
3. **Cadence matters more than completeness.** A weekly LinkedIn scrape is more valuable than a one-off perfect dataset.
4. **Internal sources are highest signal.** External scrapes are noise compared to a 200 word AE post-mortem.
5. **Synthetic and real can coexist.** For markets where we cannot legally scrape (e.g., Gong API of competitors), we use customer-supplied or synthetic data.

---

## Open question for the team

Which Tier 2 source should we wire up first?

**Recommendation:** Job postings + LinkedIn hiring data. Low cost, weekly cadence, high signal for predicting competitor product moves 3 to 6 months ahead. Pairs naturally with the Trending Intelligence section of the battle cards.
