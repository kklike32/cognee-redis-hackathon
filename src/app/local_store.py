from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .redis_client import embed_text

LOCAL_CACHE_PATH = Path(".cache") / "knowledge_chunks.json"


def _ensure_cache_dir() -> None:
    LOCAL_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_local_chunks() -> list[dict[str, Any]]:
    if not LOCAL_CACHE_PATH.exists():
        return []

    try:
        raw = json.loads(LOCAL_CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(raw, list):
        return []
    return [chunk for chunk in raw if isinstance(chunk, dict)]


def save_local_chunks(chunks: list[dict[str, Any]]) -> None:
    _ensure_cache_dir()
    existing = {chunk["id"]: chunk for chunk in load_local_chunks() if chunk.get("id")}
    for chunk in chunks:
        chunk_id = chunk.get("id")
        if not chunk_id:
            continue
        existing[chunk_id] = chunk

    LOCAL_CACHE_PATH.write_text(
        json.dumps(list(existing.values()), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    a = np.asarray(vector_a, dtype=np.float32)
    b = np.asarray(vector_b, dtype=np.float32)
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(a, b) / denominator)


def search_local_chunks(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    chunks = load_local_chunks()
    if not chunks:
        return []

    query_embedding = embed_text(query)
    scored_chunks: list[tuple[float, dict[str, Any]]] = []

    for chunk in chunks:
        embedding = chunk.get("embedding")
        if isinstance(embedding, list) and embedding:
            score = _cosine_similarity(query_embedding, embedding)
        else:
            haystack = f"{chunk.get('title', '')} {chunk.get('text', '')}".lower()
            score = sum(1 for token in query.lower().split() if token in haystack) / max(
                1, len(query.split())
            )
        scored_chunks.append((score, chunk))

    scored_chunks.sort(key=lambda item: item[0], reverse=True)

    results: list[dict[str, Any]] = []
    for score, chunk in scored_chunks[:top_k]:
        normalized = dict(chunk)
        normalized["score"] = score
        normalized["source"] = normalized.get("source", "local-cache")
        results.append(normalized)
    return results
