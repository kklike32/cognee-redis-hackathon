from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:  # pragma: no cover - optional LLM dependency
    requests = None  # type: ignore[assignment]

from .config import get_settings

ROOT = Path(__file__).resolve().parent.parent
SOURCES_DIR = ROOT / "data" / "sources"
WIKI_DIR = ROOT / "data" / "wiki"
DEEL_WIKI_PATH = WIKI_DIR / "deel.md"

LLM_ENABLE_ENV = "SHERLOCK_USE_LLM"
COGNEE_INDEX_ENV = "SHERLOCK_INDEX_COGNEE"

BATTLE_CARD_HEADINGS = [
    "Metadata",
    "Positioning Headline",
    "Quantitative Fields",
    "Strengths to Acknowledge",
    "Weaknesses to Attack",
    "Common Objections and Responses",
    "Trap-Setting Discovery Questions",
    "Customer Evidence",
    "Segment-Specific Talk Track",
    "Recent Activity",
    "Sources",
]


def build_company_wiki(company: str = "deel", use_llm: bool = True) -> dict[str, Any]:
    """Build the local markdown wiki for a supported company.

    The deterministic path is the production-safe baseline. The optional LLM
    path is intentionally gated by env and API key, and falls back on any issue.
    """

    started = time.perf_counter()
    if company.lower() != "deel":
        raise ValueError("Only company='deel' is supported.")

    source_docs = _read_source_docs(SOURCES_DIR)
    if not source_docs:
        raise FileNotFoundError(f"No markdown sources found under {SOURCES_DIR}")

    wiki_markdown = None
    generation_mode = "deterministic-fallback"
    if use_llm and _env_true(LLM_ENABLE_ENV) and _effective_llm_key():
        llm_result = _try_build_with_llm(source_docs)
        if llm_result:
            wiki_markdown = llm_result["markdown"]
            generation_mode = llm_result["model"]

    if wiki_markdown is None:
        wiki_markdown = _build_deterministic_wiki(source_docs)

    DEEL_WIKI_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEEL_WIKI_PATH.write_text(wiki_markdown, encoding="utf-8")

    cognee_status = _best_effort_cognee_status(wiki_markdown)
    latency_ms = round((time.perf_counter() - started) * 1000, 2)

    return {
        "wiki_markdown": wiki_markdown,
        "sources": _source_payload(source_docs),
        "generation_mode": generation_mode,
        "cognee_status": cognee_status,
        "latency_ms": latency_ms,
    }


def _read_source_docs(sources_dir: Path) -> list[dict[str, Any]]:
    docs = []
    for path in sorted(sources_dir.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        docs.append(
            {
                "path": path,
                "source": _display_path(path),
                "name": path.name,
                "lines": lines,
                "text": "\n".join(lines).strip(),
                "snippets": _extract_snippets(lines),
            }
        )
    return docs


def _extract_snippets(lines: list[str]) -> list[dict[str, Any]]:
    snippets = []
    for line_no, line in enumerate(lines, start=1):
        cleaned = line.strip()
        if not cleaned or cleaned.startswith("#"):
            continue
        if cleaned.startswith("-"):
            cleaned = cleaned[1:].strip()
        if _is_low_signal_metadata(cleaned):
            continue
        snippets.append({"line": line_no, "snippet": cleaned})
    return snippets


def _is_low_signal_metadata(line: str) -> bool:
    lowered = line.lower()
    metadata_prefixes = (
        "source type:",
        "date:",
        "competitor:",
        "reviewer role:",
        "account segment:",
    )
    return lowered.startswith(metadata_prefixes)


def _build_deterministic_wiki(source_docs: list[dict[str, Any]]) -> str:
    facts = _facts_by_source(source_docs)
    sources = _source_payload(source_docs)
    source_lines = "\n".join(f"- {source['source']}" for source in sources)
    evidence_lines = "\n".join(
        f"- {source['source']} line {source['line_start']}: {source['snippet']}"
        for source in sources
    )

    return f"""# Deel Battle Card

## Metadata
- Owner: Competitive Intelligence
- Last reviewed: 2026-05-16
- Confidence score: Medium
- Pending changes: 0
- Generation mode: deterministic-fallback

## Positioning Headline
Oyster is the steadier global employment partner for teams that need hands-on compliance support, predictable expansion guidance, and a sales motion built around trust.

## Quantitative Fields
- Customer count: Internal demo placeholder
- Countries served: Global employment coverage for distributed teams
- Funding / valuation: Not used in this demo
- Headcount: {facts['headcount']}
- Pricing: Validate during discovery
- Average deal size in Oyster funnel: Internal demo placeholder
- Win rate vs Deel last 90 days: Internal demo placeholder

## Strengths to Acknowledge
- Deel has clear brand recognition in competitive deals. {facts['brand']}
- Buyers may value broad platform coverage and fast setup. {facts['breadth']}
- Recent workflow automation messaging can make Deel feel like a single-place HR operations platform. {facts['automation']}

## Weaknesses to Attack
- Prospects may worry about support consistency and escalation paths after implementation. {facts['support']}
- Lean people teams without dedicated employment counsel need guided compliance help. {facts['team']}
- Automation breadth should be reframed toward the buyer's riskier first international hires. {facts['automation_reframe']}

## Common Objections and Responses
- Objection: Deel seems bigger and more established.
  Response: Acknowledge the brand, then reframe around implementation confidence, compliance guidance, and the buyer's specific expansion plan.
- Objection: We need to move quickly.
  Response: Tie speed to fewer downstream mistakes, not only contract signature speed.
- Objection: Deel has more automation.
  Response: Ask whether the buyer needs more workflow surface area or clearer country-specific support for the first risky hires.

## Trap-Setting Discovery Questions
- Which countries are highest risk for your first wave of hiring?
- Who owns local compliance decisions after the contract is signed?
- What would a bad onboarding experience cost your team in the first 90 days?
- What escalation path do you expect if a country-specific onboarding question blocks payroll or start dates?

## Customer Evidence
{evidence_lines}

## Segment-Specific Talk Track
For Seed to Series B startups, lead with risk reduction and implementation confidence. The buyer wants to expand quickly, but they usually lack a large internal legal or people operations team.

## Recent Activity
- Deel announced new workflow automation capabilities aimed at helping teams manage more HR operations in one place. {facts['automation']}

## Sources
{source_lines}
"""


def _facts_by_source(source_docs: list[dict[str, Any]]) -> dict[str, str]:
    all_snippets = [
        (doc["name"], snippet["line"], snippet["snippet"])
        for doc in source_docs
        for snippet in doc["snippets"]
    ]

    def find_any(*needle_groups: tuple[str, ...]) -> str:
        for name, line, snippet in all_snippets:
            lowered = snippet.lower()
            for needles in needle_groups:
                if all(needle in lowered for needle in needles):
                    return f"({name} line {line}: {snippet})"
        return "(No direct local source line found.)"

    return {
        "headcount": find_any(("80 employees",), ("series a fintech",)),
        "brand": find_any(("brand",), ("shortlist",)),
        "breadth": find_any(("broad",), ("platform",)),
        "automation": find_any(("workforce planning",), ("ai", "workforce"), ("hr operating system",)),
        "automation_reframe": find_any(("first international hires",), ("compliant-hiring",), ("confidence", "country-specific")),
        "support": find_any(("support",), ("country questions",), ("escalation",)),
        "team": find_any(("no in-house employment counsel",), ("do not have", "employment counsel"), ("lean people",), ("two operators",)),
    }


def _source_payload(source_docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = []
    for doc in source_docs:
        first = doc["snippets"][0] if doc["snippets"] else {"line": 1, "snippet": doc["text"][:240]}
        sources.append(
            {
                "source": doc["source"],
                "line_start": first["line"],
                "line_end": first["line"],
                "snippet": first["snippet"],
            }
        )
    return sources


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _try_build_with_llm(source_docs: list[dict[str, Any]]) -> dict[str, str] | None:
    if requests is None:
        return None

    settings = get_settings()
    model = os.getenv("SHERLOCK_LLM_MODEL") or settings.llm_model
    api_key = _effective_llm_key()
    if not api_key:
        return None

    prompt = _llm_prompt(source_docs)
    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "input": prompt,
                "max_output_tokens": 2400,
            },
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()
        markdown = _extract_output_text(payload)
    except Exception:
        return None

    if not markdown or "# Deel Battle Card" not in markdown:
        return None
    for heading in BATTLE_CARD_HEADINGS:
        if f"## {heading}" not in markdown:
            return None
    return {"markdown": markdown.strip() + "\n", "model": model}


def _llm_prompt(source_docs: list[dict[str, Any]]) -> str:
    sources = "\n\n".join(f"Source: {doc['path']}\n{doc['text']}" for doc in source_docs)
    headings = "\n".join(f"## {heading}" for heading in BATTLE_CARD_HEADINGS)
    return (
        "Build a cited Deel competitive battle card in markdown. "
        "Use exactly these section headings and include source path plus line/snippet citations. "
        "Do not invent unsupported facts.\n\n"
        f"{headings}\n\n"
        f"Local sources:\n{sources}"
    )


def _extract_output_text(payload: dict[str, Any]) -> str | None:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    output = payload.get("output")
    if not isinstance(output, list):
        return None
    parts = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for content_item in content:
            if isinstance(content_item, dict) and content_item.get("type") == "output_text":
                text = content_item.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "\n".join(parts) if parts else None


def _best_effort_cognee_status(wiki_markdown: str) -> str:
    try:
        import cognee
    except ImportError:
        return "missing"

    if not _env_true(COGNEE_INDEX_ENV):
        return "missing"

    settings = get_settings()

    async def add_wiki() -> str:
        try:
            await cognee.add(wiki_markdown, dataset_name=settings.cognee_dataset_name)
            if settings.cognee_skip_cognify or settings.mock_embedding or not settings.llm_api_key:
                return "added_not_cognified"
            await cognee.cognify(datasets=[settings.cognee_dataset_name])
            return "indexed"
        except Exception:
            return "error"

    try:
        return asyncio.run(add_wiki())
    except Exception:
        return "error"


def _effective_llm_key() -> str | None:
    return os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")


def _env_true(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}
