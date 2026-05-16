from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cache import build_cache_key, get_cached_brief, set_cached_brief
from .citations import build_citations, citation_ref, format_citations_markdown
from .config import Settings, get_settings
from .markdown_store import read_wiki, wiki_path
from .retrieval import retrieve_context_with_status

SYSTEM_PROMPT = """You are Sherlock, a competitive-card agent for Oyster HR.
Generate a deal-specific competitive brief for Oyster HR competing against Deel.
Be accurate, concise, and useful to a sales team. Do not invent unsupported facts.
Every factual competitive claim must cite the battle card, Gong-style source,
G2-style source, or product launch source. Tailor the answer to the deal context
and avoid generic sales fluff."""


@dataclass(frozen=True)
class BriefResult:
    markdown: str
    citations: list[dict[str, Any]]
    cache_status: str
    latency_ms: int
    retrieval_status: dict[str, str]
    cache_key: str
    model_used: str = "deterministic-fallback"

    def as_dict(self) -> dict[str, Any]:
        return {
            "markdown": self.markdown,
            "brief_markdown": self.markdown,
            "citations": self.citations,
            "sources": self.citations,
            "cache_status": self.cache_status,
            "latency_ms": self.latency_ms,
            "retrieval_status": self.retrieval_status,
            "cache_key": self.cache_key,
            "model_used": self.model_used,
        }


def _source_paths(settings: Settings) -> list[Path]:
    return sorted(settings.sources_dir.glob("*.md"))


def _citation_for(citations: list[dict[str, Any]], source_kind: str, fallback: int = 0) -> str:
    for citation in citations:
        if citation.get("source_type") == source_kind:
            return f"[{citation['id']}]"
    return citation_ref(citations, fallback)


def _source_evidence(citations: list[dict[str, Any]], source_kind: str, fallback: int = 0) -> str:
    for citation in citations:
        if citation.get("source_type") == source_kind:
            return str(citation.get("snippet", "")).strip()
    if citations:
        safe_index = max(0, min(fallback, len(citations) - 1))
        return str(citations[safe_index].get("snippet", "")).strip()
    return "No local source evidence was available. Run ingestion to populate demo chunks."


def _fallback_brief(
    competitor: str,
    deal_context: str,
    wiki: str,
    chunks: list[dict[str, Any]],
    citations: list[dict[str, Any]],
) -> str:
    battle = _citation_for(citations, "battle card", 0)
    gong = _citation_for(citations, "Gong-style source", 1)
    g2 = _citation_for(citations, "G2-style source", 2)
    launch = _citation_for(citations, "product launch source", 3)
    approved_signal = ""
    if "sherlock-approved" in wiki:
        approved_signal = (
            "\n- Include the approved analyst note in the talk track: emphasize named "
            f"compliance ownership for first hires in Canada or the UK. {battle}"
        )
    context = deal_context.strip() or "No deal context provided."
    evidence_snapshot = "\n".join(
        [
            f"- Battle card: {_source_evidence(citations, 'battle card', 0)} {battle}",
            f"- Gong-style source: {_source_evidence(citations, 'Gong-style source', 1)} {gong}",
            f"- G2-style source: {_source_evidence(citations, 'G2-style source', 2)} {g2}",
            f"- Product launch source: {_source_evidence(citations, 'product launch source', 3)} {launch}",
        ]
    )
    return f"""# Competitive Brief: Oyster HR vs {competitor.title()}

## Executive summary
- Deal context: {context}
- Deel has brand awareness and a broad global HR platform story, but Oyster should redirect this buyer to guided compliance, predictable rollout support, and sales-to-success continuity. {battle} {launch}
- For this deal, the strongest wedge is the buyer's need for confident Canada and UK expansion without unclear post-sale compliance ownership or surprise add-ons. {gong} {g2}

## Strengths to acknowledge
- Deel is often shortlisted because buyers recognize the brand in global hiring and payroll conversations. {battle}
- Deel's broader platform narrative can appeal to executives who want many HR capabilities from one vendor. {battle} {launch}
- Deel can be associated with speed and easy initial onboarding, especially for contractor workflows. {g2}

## Weaknesses to attack
- The demo evidence shows buyer uncertainty around who owns nuanced compliance questions after the sale. {battle} {gong}
- Packaging and add-on clarity can become a procurement issue when teams expand from contractors to full-time employees. {g2}
- Deel's broad AI workforce-planning story can be reframed as less urgent than compliant first hires for an early-stage expansion. {launch}

## Likely objections
- "Deel seems bigger." Acknowledge the brand, then ask who will own country-specific compliance answers after launch. {battle} {gong}
- "We want one global HR platform." Redirect from feature breadth to the operational risk of getting the first Canada and UK hires right. {battle} {launch}
- "Deel looks fast." Agree that speed matters, then separate fast onboarding from clear scope, support ownership, and predictable total cost. {g2}

## Recommended talk track
- "Deel is a strong brand, and it makes sense that your CEO knows them. For this decision, I would focus less on the size of the platform and more on who will guide your first Canada and UK hires when nuanced employment questions come up after signature." {gong}
- "Oyster's fit is strongest when a lean team needs a calmer expansion path: guided hiring, practical rollout support, and clarity on what is included before finance has to normalize add-ons." {battle} {g2}
{approved_signal}

## Trap-setting discovery questions
- "When a country-specific employment question comes up after launch, who on the vendor side do you expect to own the answer?" {battle} {gong}
- "Which services in the proposal are included, and which are add-ons your finance team needs to normalize before the board meeting?" {g2}
- "Is the urgent problem AI workforce planning, or is it confidently hiring your next employees in Canada and the UK this quarter?" {launch}

## Source citations
{evidence_snapshot}

{format_citations_markdown(citations)}
"""


def _build_llm_prompt(
    competitor: str,
    deal_context: str,
    wiki: str,
    citations: list[dict[str, Any]],
) -> str:
    sources = "\n\n".join(
        f"[{citation['id']}] {citation['source']} ({citation.get('source_type')}), "
        f"{citation.get('heading')}:\n{citation.get('snippet')}"
        for citation in citations
    )
    return f"""{SYSTEM_PROMPT}

Required sections:
- Executive summary
- Strengths to acknowledge
- Weaknesses to attack
- Likely objections
- Recommended talk track
- Trap-setting discovery questions
- Source citations

Competitor: {competitor}
Deal context: {deal_context}

Battle card markdown:
{wiki[:6000]}

Retrieved cited evidence:
{sources}
"""


def _extract_openai_text(payload: dict[str, Any]) -> str | None:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    output = payload.get("output")
    if not isinstance(output, list):
        return None
    texts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    texts.append(text)
    return "\n".join(texts) if texts else None


def _try_llm_brief(
    competitor: str,
    deal_context: str,
    wiki: str,
    citations: list[dict[str, Any]],
    settings: Settings,
) -> tuple[str | None, str]:
    if not settings.llm_api_key or os.getenv("SHERLOCK_USE_LLM", "").lower() not in {"1", "true", "yes"}:
        return None, "deterministic-fallback"
    try:
        import requests

        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.llm_model,
                "input": _build_llm_prompt(competitor, deal_context, wiki, citations),
                "max_output_tokens": 1400,
            },
            timeout=30,
        )
        response.raise_for_status()
        text = _extract_openai_text(response.json())
    except Exception:
        return None, "deterministic-fallback"
    if not text or "Source citations" not in text:
        return None, "deterministic-fallback"
    return text.strip(), settings.llm_model


def _normalize_cached_payload(value: dict[str, Any]) -> dict[str, Any]:
    markdown = value.get("brief_markdown") or value.get("markdown") or ""
    sources = value.get("sources") or value.get("citations") or []
    return {
        "brief_markdown": markdown,
        "markdown": markdown,
        "sources": sources,
        "citations": sources,
        "retrieval_status": value.get("retrieval_status", {}),
        "model_used": value.get("model_used", "deterministic-fallback"),
    }


def generate_competitive_brief(
    competitor: str,
    deal_context: str,
    use_cache: bool = True,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    start = time.perf_counter()
    competitor = competitor.lower().strip() or settings.default_competitor
    wiki_file = wiki_path(competitor, settings)
    source_files = _source_paths(settings)
    cache_key = build_cache_key(competitor, deal_context, wiki_file, source_files)

    cached = None
    if use_cache:
        cached = get_cached_brief(cache_key, settings=settings)
        if cached.status == "hit" and cached.value:
            elapsed = int((time.perf_counter() - start) * 1000)
            payload = _normalize_cached_payload(cached.value)
            return {
                **payload,
                "cache_status": "hit",
                "latency_ms": elapsed,
                "cache_key": cache_key,
            }

    query = (
        f"Oyster HR versus {competitor} competitive battle card. Deal context: {deal_context}. "
        "Prioritize compliance ownership, onboarding speed, support model, pricing clarity, "
        "Canada, UK, Series A, fintech."
    )
    retrieval = retrieve_context_with_status(query, competitor=competitor, top_k=8, settings=settings)
    citations = build_citations(retrieval.chunks)
    wiki = read_wiki(competitor, settings)
    llm_markdown, model_used = _try_llm_brief(competitor, deal_context, wiki, citations, settings)
    markdown = llm_markdown or _fallback_brief(competitor, deal_context, wiki, retrieval.chunks, citations)
    payload = {
        "brief_markdown": markdown,
        "markdown": markdown,
        "sources": citations,
        "citations": citations,
        "retrieval_status": retrieval.source_status,
        "model_used": model_used,
    }

    cache_status = "disabled"
    if use_cache and cached is not None and cached.status != "unavailable":
        cache_status = "miss"
        set_cached_brief(cache_key, payload, settings=settings)

    elapsed = int((time.perf_counter() - start) * 1000)
    return {
        **payload,
        "cache_status": cache_status,
        "latency_ms": elapsed,
        "cache_key": cache_key,
    }


def generate_brief(
    competitor: str = "deel",
    deal_context: str = "",
    use_cache: bool = True,
    settings: Settings | None = None,
) -> BriefResult:
    payload = generate_competitive_brief(
        competitor=competitor,
        deal_context=deal_context,
        use_cache=use_cache,
        settings=settings,
    )
    return BriefResult(
        markdown=payload["brief_markdown"],
        citations=payload["sources"],
        cache_status=payload["cache_status"],
        latency_ms=payload["latency_ms"],
        retrieval_status=payload["retrieval_status"],
        cache_key=payload["cache_key"],
        model_used=payload["model_used"],
    )
