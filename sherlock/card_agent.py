from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cache import build_cache_key, get_cached_brief, set_cached_brief
from .citations import build_citations, citation_ref, format_citations_markdown
from .config import Settings, get_settings
from .markdown_store import read_wiki, wiki_path
from .retrieval import retrieve_context


@dataclass(frozen=True)
class BriefResult:
    markdown: str
    citations: list[dict[str, Any]]
    cache_status: str
    latency_ms: int
    retrieval_status: dict[str, str]
    cache_key: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "markdown": self.markdown,
            "citations": self.citations,
            "cache_status": self.cache_status,
            "latency_ms": self.latency_ms,
            "retrieval_status": self.retrieval_status,
            "cache_key": self.cache_key,
        }


def _source_paths(settings: Settings) -> list[Path]:
    return sorted(settings.sources_dir.glob("*.md"))


def _fallback_brief(
    competitor: str,
    deal_context: str,
    wiki: str,
    chunks: list[dict[str, Any]],
    citations: list[dict[str, Any]],
) -> str:
    c0 = citation_ref(citations, 0)
    c1 = citation_ref(citations, 1)
    c2 = citation_ref(citations, 2)
    approved_signal = ""
    if "sherlock-approved" in wiki:
        approved_signal = (
            "\n- Recently approved analyst note: emphasize named compliance ownership "
            f"for first hires in Canada or the UK. {c0}"
        )
    snippets = [str(chunk.get("text", "")).strip() for chunk in chunks[:3]]
    evidence_line = snippets[0][:220] if snippets else "Run ingestion to populate local source evidence."
    return f"""### Competitive Brief: Oyster vs {competitor.title()}

**Deal context:** {deal_context.strip() or "No deal context provided."}

**Recommended talk track**
- Acknowledge Deel's brand and broad platform story, then move the buyer back to the operational risk in this deal: compliant first hires, clear ownership after go-live, and predictable rollout support. {c0}
- For this account, frame Oyster as the guided path for a lean team expanding internationally without in-house employment counsel. {c1}
{approved_signal}

**Strengths to acknowledge**
- Deel is recognizable and often starts on the shortlist. {c0}
- Deel's broad HR platform story may appeal to executives who want a single vendor narrative. {c2}

**Weaknesses to attack**
- Buyers may struggle to understand packaging, add-ons, and who owns nuanced compliance questions after onboarding. {c0}
- A broad platform story can distract from the buyer's immediate need: getting the next Canada and UK hires right this quarter. {c2}

**Objections and responses**
- "Deel is bigger." Response: "That brand strength is real. The question is who will own the country-specific employment decisions once your team is live." {c0}
- "We want one platform." Response: "For this stage, the critical decision is the safest expansion path, not the largest feature catalog." {c2}

**Discovery questions**
- "Who do you expect to answer nuanced compliance questions after the contract is signed?"
- "Which add-ons are required for your Canada and UK hiring plan?"
- "Is the board optimizing for platform breadth or confidence in the first international hires?"

**Evidence snapshot**
{evidence_line}

### Citations
{format_citations_markdown(citations)}
"""


def generate_brief(
    competitor: str = "deel",
    deal_context: str = "",
    settings: Settings | None = None,
) -> BriefResult:
    settings = settings or get_settings()
    start = time.perf_counter()
    competitor = competitor.lower()
    wiki_file = wiki_path(competitor, settings)
    source_files = _source_paths(settings)
    cache_key = build_cache_key(competitor, deal_context, wiki_file, source_files)
    cached = get_cached_brief(cache_key, settings=settings)
    if cached.status == "hit" and cached.value:
        elapsed = int((time.perf_counter() - start) * 1000)
        value = cached.value
        return BriefResult(
            markdown=value["markdown"],
            citations=value.get("citations", []),
            cache_status="hit",
            latency_ms=elapsed,
            retrieval_status=value.get("retrieval_status", {}),
            cache_key=cache_key,
        )

    query = f"{competitor} competitive battle card {deal_context}"
    retrieval = retrieve_context(query, top_k=6, settings=settings)
    citations = build_citations(retrieval.chunks)
    wiki = read_wiki(competitor, settings)
    markdown = _fallback_brief(competitor, deal_context, wiki, retrieval.chunks, citations)
    payload = {
        "markdown": markdown,
        "citations": citations,
        "retrieval_status": retrieval.source_status,
    }
    stored = set_cached_brief(cache_key, payload, settings=settings)
    elapsed = int((time.perf_counter() - start) * 1000)
    status = cached.status if cached.status in {"miss", "unavailable"} else "miss"
    if status == "miss" and stored:
        status = "miss; stored"
    return BriefResult(
        markdown=markdown,
        citations=citations,
        cache_status=status,
        latency_ms=elapsed,
        retrieval_status=retrieval.source_status,
        cache_key=cache_key,
    )
