from __future__ import annotations

from pathlib import Path
from typing import Any


def _clean_source_name(source: str) -> str:
    path = Path(source)
    return path.name if path.name else source


def source_type(source: str) -> str:
    name = _clean_source_name(source).lower()
    if name == "deel.md" or "battle" in name or "/wiki/" in source.lower():
        return "battle card"
    if "gong" in name:
        return "Gong-style source"
    if "g2" in name:
        return "G2-style source"
    if "launch" in name or "product" in name:
        return "product launch source"
    return "local source"


def build_citations(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for chunk in chunks:
        source = str(chunk.get("source", "unknown"))
        metadata = chunk.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
        key = f"{source}:{metadata.get('chunk_index', len(citations))}"
        if key in seen:
            continue
        seen.add(key)
        label = f"S{len(citations) + 1}"
        citations.append(
            {
                "id": label,
                "source": _clean_source_name(source),
                "source_path": source,
                "source_type": source_type(source),
                "heading": metadata.get("heading_path") or chunk.get("title") or "Source",
                "line_start": metadata.get("line_start"),
                "line_end": metadata.get("line_end"),
                "snippet": str(chunk.get("text", "")).strip()[:360],
            }
        )
    return citations


def citation_ref(citations: list[dict[str, Any]], index: int = 0) -> str:
    if not citations:
        return ""
    safe_index = max(0, min(index, len(citations) - 1))
    return f"[{citations[safe_index]['id']}]"


def format_citations_markdown(citations: list[dict[str, Any]]) -> str:
    if not citations:
        return "_No citations found. Run ingestion to add local source chunks._"
    lines = []
    for citation in citations:
        location = ""
        if citation.get("line_start") and citation.get("line_end"):
            location = f", lines {citation['line_start']}-{citation['line_end']}"
        source_kind = citation.get("source_type", "local source")
        lines.append(
            f"- [{citation['id']}] {citation['source']} ({source_kind}) - "
            f"{citation['heading']}{location}: "
            f"{citation['snippet']}"
        )
    return "\n".join(lines)
