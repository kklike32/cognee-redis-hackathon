from __future__ import annotations

from typing import Any

from .cognee_client import CogneeClient
from .config import get_settings
from .local_store import search_local_chunks
from .redis_client import search_knowledge_chunks


def _chunk_key(chunk: dict[str, Any]) -> str:
    title = str(chunk.get("title", "")).strip().lower()
    text = str(chunk.get("text", "")).strip().lower()
    source = str(chunk.get("source", "")).strip().lower()
    return f"{title}|{text}|{source}"


def _normalize_chunk(chunk: dict[str, Any], source: str) -> dict[str, Any]:
    normalized = dict(chunk)
    normalized.setdefault("source", source)
    normalized.setdefault("score", 0.0)
    return normalized


def retrieve_context(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    settings = get_settings()
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    for source_name, chunks in (
        ("cognee", CogneeClient(settings).search(query, top_k=top_k)),
        ("redis", search_knowledge_chunks(query, top_k=top_k, settings=settings)),
        ("local-cache", search_local_chunks(query, top_k=top_k)),
    ):
        for chunk in chunks:
            normalized = _normalize_chunk(chunk, source_name)
            key = _chunk_key(normalized)
            if key in seen:
                continue
            seen.add(key)
            results.append(normalized)
            if len(results) >= top_k:
                return results

    return results

