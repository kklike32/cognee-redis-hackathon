from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cache import build_cache_key, get_cached_brief, set_cached_brief
from .citations import build_citations, citation_ref, format_citations_markdown
from .config import Settings, get_settings
from .markdown_store import read_wiki, wiki_path
from .retrieval import retrieve_context_with_status

SYSTEM_PROMPT = """You are Sherlock, an internal competitive-card agent for Oyster HR.
Generate a deal-specific competitive brief for Oyster HR competing against Deel.
Be accurate, concise, and useful to sales. Do not invent unsupported facts.
Every factual competitive claim must cite the Deel knowledge wiki, Gong-style source,
G2-style source, product launch source, or another internal source."""


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
            "brief": self.markdown,
            "markdown": self.markdown,
            "brief_markdown": self.markdown,
            "sources": self.citations,
            "citations": self.citations,
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


def _extract_recent_updates(wiki: str) -> str:
    approved_blocks = re.findall(
        r"<!-- sherlock-approved:[^:]+:start -->(.*?)<!-- sherlock-approved:[^:]+:end -->",
        wiki,
        flags=re.DOTALL,
    )
    if approved_blocks:
        return "\n".join(block.strip() for block in approved_blocks if block.strip())
    marker = "## Recent Analyst-Approved Updates"
    if marker not in wiki:
        return ""
    return wiki.split(marker, 1)[1].strip()


def _fallback_brief(
    competitor: str,
    deal_context: str,
    wiki: str,
    citations: list[dict[str, Any]],
) -> str:
    battle = _citation_for(citations, "battle card", 0)
    gong = _citation_for(citations, "Gong-style source", 1)
    g2 = _citation_for(citations, "G2-style source", 2)
    launch = _citation_for(citations, "product launch source", 3)
    context = deal_context.strip() or "No specific deal context provided."
    approved = _extract_recent_updates(wiki)
    approved_line = ""
    if approved:
        first_line = next((line.strip("- ").strip() for line in approved.splitlines() if line.strip() and not line.startswith("###")), "")
        if first_line:
            approved_line = f"\n- Analyst-approved update to include: {first_line} {battle}"

    return f"""# Sherlock AE Brief: Oyster HR vs {competitor.title()}

## Executive summary
- Deal context: {context}
- Acknowledge Deel's brand and platform breadth, then redirect to Oyster's guided compliance posture and implementation confidence for lean international hiring teams. {battle} {launch}
- For this deal, focus on Canada/UK expansion, post-signature compliance ownership, onboarding support, and predictable scope. {gong} {g2}

## Strengths to acknowledge
- Deel is well known and often enters deals through brand recognition. {battle}
- Buyers may value Deel's broad platform story and fast setup. {battle} {g2}
- Deel's automation messaging can sound attractive to teams seeking more HR operations in one place. {launch}

## Weaknesses to attack
- The Gong-style deal evidence shows uncertainty about compliance support after implementation. {gong}
- Lean people teams care deeply about support responsiveness when edge cases appear. {g2}
- A broad automation narrative can distract from the immediate risk: getting the first international hires right. {launch}

## Likely objections
- "Deel seems bigger." Response: "That brand recognition is real. For this expansion, the bigger question is who owns country-specific compliance guidance after signature." {battle} {gong}
- "We need speed." Response: "Speed matters, but for Canada and the UK it has to include country checklists, escalation paths, and fewer downstream mistakes." {gong}
- "Deel has broader automation." Response: "Automation helps once the operating model is clear. First, confirm the compliant hiring path and support model." {launch}

## Recommended talk track
- "For an 80-person fintech expanding into Canada and the UK, I would separate platform breadth from execution confidence. Deel is credible, but Oyster is the steadier fit when a lean team needs guided compliance handoffs and practical onboarding support." {battle} {gong}
- "Before the board meeting, normalize what is included, what is an add-on, and who answers nuanced country questions after implementation." {g2}
{approved_line}

## Trap-setting discovery questions
- "Who owns country-specific employment decisions after the contract is signed?" {battle} {gong}
- "Which onboarding support is included for Canada and the UK, and where are the escalation paths documented?" {gong}
- "Are you solving an immediate compliant-hiring problem or a broader HR automation problem?" {launch}

## Source citations
{format_citations_markdown(citations)}
"""


def _build_llm_prompt(competitor: str, deal_context: str, wiki: str, citations: list[dict[str, Any]]) -> str:
    sources = "\n\n".join(
        f"[{citation['id']}] {citation['source']} ({citation.get('source_type')}):\n{citation.get('snippet')}"
        for citation in citations
    )
    return f"""{SYSTEM_PROMPT}

Required sections:
Executive summary
Strengths to acknowledge
Weaknesses to attack
Likely objections
Recommended talk track
Trap-setting discovery questions
Source citations

Competitor: {competitor}
Deal context: {deal_context}

Deel knowledge wiki:
{wiki[:6000]}

Retrieved sources:
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
    markdown = value.get("brief_markdown") or value.get("markdown") or value.get("brief") or ""
    sources = value.get("sources") or value.get("citations") or []
    return {
        "brief": markdown,
        "brief_markdown": markdown,
        "markdown": markdown,
        "sources": sources,
        "citations": sources,
        "retrieval_status": value.get("retrieval_status", {}),
        "model_used": value.get("model_used", "deterministic-fallback"),
    }


def generate_competitive_brief(
    competitor: str = "deel",
    deal_context: str = "",
    use_cache: bool = True,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    start = time.perf_counter()
    competitor = competitor.lower().strip() or "deel"
    if competitor != "deel":
        raise ValueError("Sherlock demo is scoped to Deel only.")

    wiki_file = wiki_path("deel", settings)
    source_files = _source_paths(settings)
    cache_key = build_cache_key(competitor, deal_context, wiki_file, source_files)

    cached = None
    if use_cache:
        cached = get_cached_brief(cache_key, settings=settings)
        if cached.status == "hit" and cached.value:
            payload = _normalize_cached_payload(cached.value)
            return {
                **payload,
                "cache_status": "hit",
                "latency_ms": int((time.perf_counter() - start) * 1000),
                "cache_key": cache_key,
            }

    query = (
        f"Oyster HR versus Deel battle card. Deal context: {deal_context}. "
        "Canada UK compliance ownership onboarding support predictable pricing support responsiveness."
    )
    retrieval = retrieve_context_with_status(query, company="deel", top_k=8, settings=settings)
    citations = build_citations(retrieval.chunks)
    wiki = read_wiki("deel", settings)
    llm_markdown, model_used = _try_llm_brief(competitor, deal_context, wiki, citations, settings)
    markdown = llm_markdown or _fallback_brief(competitor, deal_context, wiki, citations)
    payload = {
        "brief": markdown,
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

    return {
        **payload,
        "cache_status": cache_status,
        "latency_ms": int((time.perf_counter() - start) * 1000),
        "cache_key": cache_key,
    }


def generate_brief(
    competitor: str = "deel",
    deal_context: str = "",
    use_cache: bool = True,
    settings: Settings | None = None,
) -> BriefResult:
    payload = generate_competitive_brief(competitor, deal_context, use_cache=use_cache, settings=settings)
    return BriefResult(
        markdown=payload["brief_markdown"],
        citations=payload["sources"],
        cache_status=payload["cache_status"],
        latency_ms=payload["latency_ms"],
        retrieval_status=payload["retrieval_status"],
        cache_key=payload["cache_key"],
        model_used=payload["model_used"],
    )
