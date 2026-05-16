# FounderOS Memory Wiki

## Problem

Founders waste time repeating market research, competitor analysis, customer discovery notes, and investor feedback across scattered docs.

Teams also lose the connection between a customer objection, a pricing discussion, and the underlying market context.

## Solution

A persistent LLM-readable company memory wiki backed by Cognee and Redis.

The system turns notes, research docs, and meeting transcripts into reusable knowledge chunks that can be retrieved by specialized agents.

## Target Users

- Early-stage founders
- GTM teams
- Product marketers
- Startup operators

## Use Cases

- Market research synthesis
- Competitor tracking
- ICP refinement
- Pricing research
- Customer objection memory
- Investor narrative generation

## Initial GTM Hypothesis

The first wedge should focus on founders who already have lots of scattered research but no durable memory layer.

The strongest message is not "search your docs". It is "remember what your team already learned, and make every future answer better."

## Notes

- Redis Cloud should hold the vector/cache layer for fast retrieval.
- Cognee should act as the knowledge plane and memory system.
- RedisVL should provide a clean schema and retrieval demo.
- Future agents can specialize in market, competitor, customer, and pricing research.

