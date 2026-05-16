from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Settings, get_settings

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass(frozen=True)
class RetrievalResult:
    chunks: list[dict[str, Any]]
    source_status: dict[str, str]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "document"


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 2}


def _score(query: str, chunk: dict[str, Any]) -> float:
    q = _tokens(query)
    haystack = _tokens(f"{chunk.get('title', '')} {chunk.get('text', '')} {chunk.get('source', '')}")
    if not q:
        return 0.0
    overlap = len(q & haystack) / len(q)
    source_bonus = 0.08 if "wiki" in str(chunk.get("source", "")) else 0.0
    return overlap + source_bonus


def split_markdown(path: Path, competitor: str = "deel") -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    heading_stack: list[tuple[int, str]] = []
    chunks: list[dict[str, Any]] = []
    buffer: list[tuple[int, str]] = []

    def heading_path() -> str:
        return " > ".join(item[1] for item in heading_stack) or path.stem

    def flush() -> None:
        if not buffer:
            return
        content = "\n".join(line for _, line in buffer).strip()
        start = buffer[0][0]
        end = buffer[-1][0]
        buffer.clear()
        if not content:
            return
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
        for paragraph in paragraphs:
            chunk_id = hashlib.sha1(f"{path}:{start}:{paragraph}".encode("utf-8")).hexdigest()
            chunks.append(
                {
                    "id": chunk_id,
                    "title": heading_path(),
                    "text": paragraph,
                    "source": str(path),
                    "metadata": {
                        "competitor": competitor,
                        "document_id": _slug(path.stem),
                        "heading_path": heading_path(),
                        "chunk_index": len(chunks),
                        "line_start": start,
                        "line_end": end,
                    },
                }
            )

    for line_no, line in enumerate(lines, start=1):
        match = HEADING_RE.match(line)
        if match:
            flush()
            level = len(match.group(1))
            heading = match.group(2).strip()
            heading_stack[:] = [(h_level, h_title) for h_level, h_title in heading_stack if h_level < level]
            heading_stack.append((level, heading))
            continue
        buffer.append((line_no, line))
    flush()
    return chunks


def load_local_chunks(settings: Settings | None = None) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    if not settings.local_chunk_path.exists():
        return []
    try:
        raw = json.loads(settings.local_chunk_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return raw if isinstance(raw, list) else []


def _markdown_paths(settings: Settings, competitor: str) -> list[Path]:
    paths = [settings.wiki_dir / f"{competitor.lower()}.md"]
    paths.extend(sorted(settings.sources_dir.glob("*.md")))
    return [path for path in paths if path.exists()]


def _load_searchable_chunks(settings: Settings, competitor: str) -> list[dict[str, Any]]:
    chunks = load_local_chunks(settings)
    if chunks:
        return chunks

    markdown_chunks: list[dict[str, Any]] = []
    for path in _markdown_paths(settings, competitor):
        markdown_chunks.extend(split_markdown(path, competitor=competitor))
    return markdown_chunks


def save_local_chunks(chunks: list[dict[str, Any]], settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    settings.local_chunk_path.parent.mkdir(parents=True, exist_ok=True)
    settings.local_chunk_path.write_text(json.dumps(chunks, indent=2), encoding="utf-8")


def _decorate_results(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    decorated = []
    for index, chunk in enumerate(chunks, start=1):
        item = dict(chunk)
        metadata = item.get("metadata") or {}
        if not isinstance(metadata, dict):
            metadata = {}
            item["metadata"] = metadata
        source_path = str(item.get("source_path") or item.get("source") or "")
        source_id = str(metadata.get("document_id") or _slug(Path(source_path).stem))
        item.setdefault("source", source_path)
        item["source_path"] = source_path
        item["source_id"] = source_id
        item["citation_label"] = f"S{index}"
        item.setdefault("title", metadata.get("heading_path") or source_id)
        item.setdefault("text", "")
        decorated.append(item)
    return decorated


def search_local(
    query: str,
    competitor: str = "deel",
    top_k: int = 6,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    chunks = _load_searchable_chunks(settings, competitor)
    competitor = competitor.lower()
    chunks = [
        chunk
        for chunk in chunks
        if (chunk.get("metadata") or {}).get("competitor", competitor).lower() == competitor
    ]
    scored = sorted(
        ((_score(query, chunk), chunk) for chunk in chunks),
        key=lambda item: item[0],
        reverse=True,
    )
    results = []
    for score, chunk in scored[:top_k]:
        item = dict(chunk)
        item["score"] = round(score, 4)
        item["retrieval_source"] = "local"
        results.append(item)
    return results


def search_cognee(query: str, top_k: int, settings: Settings | None = None) -> tuple[list[dict[str, Any]], str]:
    settings = settings or get_settings()
    try:
        import cognee
        from cognee import SearchType
    except ImportError:
        return [], "missing"
    try:
        import asyncio

        async def _search():
            return await cognee.search(
                query_text=query,
                query_type=SearchType.CHUNKS,
                datasets=[settings.cognee_dataset_name],
                top_k=top_k,
            )

        raw_results = asyncio.run(_search())
    except Exception as exc:
        return [], f"error: {exc}"
    normalized = []
    for item in raw_results or []:
        if isinstance(item, dict):
            chunk = dict(item)
        elif hasattr(item, "model_dump"):
            chunk = item.model_dump()
        else:
            chunk = {"text": str(item)}
        chunk["retrieval_source"] = "cognee"
        normalized.append(chunk)
    return normalized[:top_k], "ok"


def retrieve_context_with_status(
    query: str,
    competitor: str = "deel",
    top_k: int = 6,
    settings: Settings | None = None,
) -> RetrievalResult:
    settings = settings or get_settings()
    cognee_chunks, cognee_status = search_cognee(query, top_k=top_k, settings=settings)
    local_chunks = search_local(query, competitor=competitor, top_k=top_k, settings=settings)
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for chunk in [*cognee_chunks, *local_chunks]:
        key = f"{chunk.get('source')}:{chunk.get('text')}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(chunk)
        if len(merged) >= top_k:
            break
    return RetrievalResult(
        chunks=merged,
        source_status={
            "cognee": cognee_status,
            "local": "ok" if local_chunks else "empty",
        },
    )


def retrieve_context(
    query: str,
    competitor: str = "deel",
    top_k: int = 6,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    if isinstance(competitor, int):
        top_k = competitor
        competitor = "deel"
    result = retrieve_context_with_status(
        query=query,
        competitor=competitor,
        top_k=top_k,
        settings=settings,
    )
    return _decorate_results(result.chunks)
