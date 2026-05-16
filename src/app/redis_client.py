from __future__ import annotations

import hashlib
import json
from urllib.parse import urlparse, urlunparse
from typing import Any

import numpy as np

from .config import Settings, get_settings

try:  # Optional at import time for easier local inspection.
    import redis
except ImportError:  # pragma: no cover - dependency issue is surfaced at runtime.
    redis = None  # type: ignore[assignment]

try:
    from redisvl.index import SearchIndex
    from redisvl.query import VectorQuery
    from redisvl.schema import IndexSchema
except ImportError:  # pragma: no cover - dependency issue is surfaced at runtime.
    SearchIndex = None  # type: ignore[assignment]
    VectorQuery = None  # type: ignore[assignment]
    IndexSchema = None  # type: ignore[assignment]


EMBEDDING_DIMENSIONS = 384
KNOWLEDGE_INDEX_NAME = "founderos-knowledge"
KNOWLEDGE_INDEX_PREFIX = "founderos:knowledge"


def embed_text(text: str, dimensions: int = EMBEDDING_DIMENSIONS) -> list[float]:
    """Deterministic placeholder embedding.

    Replace this with OpenAI, Cohere, Voyage, etc. once you wire a real vector
    provider into the demo.
    """

    seed_bytes = hashlib.sha256(text.encode("utf-8")).digest()
    seed = int.from_bytes(seed_bytes[:8], "big", signed=False)
    rng = np.random.default_rng(seed)
    vector = rng.standard_normal(dimensions).astype(np.float32)
    norm = float(np.linalg.norm(vector))
    if norm:
        vector = vector / norm
    return vector.tolist()


def build_redis_url(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    return settings.redis_dsn


def redact_redis_url(redis_url: str) -> str:
    parsed = urlparse(redis_url)
    if parsed.password:
        netloc = parsed.hostname or ""
        if parsed.username:
            netloc = f"{parsed.username}:***@{netloc}"
        else:
            netloc = f"***@{netloc}"
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        parsed = parsed._replace(netloc=netloc)
    return urlunparse(parsed)


def create_redis_client(settings: Settings | None = None):
    settings = settings or get_settings()
    if redis is None:  # pragma: no cover - runtime dependency guard
        raise RuntimeError("redis is not installed. Run `pip install -e .` first.")

    if settings.redis_url:
        redis_url = settings.redis_url
        if settings.redis_ssl and redis_url.startswith("redis://"):
            redis_url = "rediss://" + redis_url[len("redis://") :]
        return redis.Redis.from_url(
            redis_url,
            decode_responses=True,
        )

    if not settings.redis_host:
        raise ValueError(
            "Redis is not configured. Set REDIS_URL or REDIS_HOST in your environment."
        )

    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port or 6379,
        username=settings.redis_username,
        password=settings.redis_password,
        ssl=settings.redis_ssl,
        decode_responses=True,
    )


def ping_redis(client: Any | None = None, settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    if not settings.has_redis_config and client is None:
        if settings.has_redis_management_config:
            extra = (
                "You have Redis Cloud REST API keys, but the Redis client still needs "
                "REDIS_URL or REDIS_HOST/REDIS_PORT/REDIS_USERNAME/REDIS_PASSWORD."
            )
        else:
            extra = (
                "Set REDIS_URL or REDIS_HOST/REDIS_PORT/REDIS_USERNAME/REDIS_PASSWORD. "
                "The account/API keys are for the Redis Cloud REST API, not the Redis protocol client."
            )
        return {
            "ok": False,
            "redis_url": "",
            "message": f"Redis is not configured. {extra}",
        }

    try:
        redis_client = client or create_redis_client(settings)
        ok = bool(redis_client.ping())
        return {
            "ok": ok,
            "redis_url": redact_redis_url(build_redis_url(settings)),
            "message": "Redis ping succeeded" if ok else "Redis ping failed",
        }
    except Exception as exc:  # pragma: no cover - surfaced in CLI output.
        return {
            "ok": False,
            "redis_url": redact_redis_url(build_redis_url(settings)),
            "message": f"Redis ping failed: {exc}",
        }


def build_knowledge_schema():
    if IndexSchema is None:  # pragma: no cover
        raise RuntimeError("redisvl is not installed. Run `pip install -e .` first.")

    return IndexSchema.from_dict(
        {
            "index": {
                "name": KNOWLEDGE_INDEX_NAME,
                "prefix": KNOWLEDGE_INDEX_PREFIX,
                "storage_type": "json",
            },
            "fields": [
                {"name": "id", "type": "tag"},
                {"name": "title", "type": "text", "attrs": {"sortable": True}},
                {"name": "text", "type": "text"},
                {"name": "source", "type": "tag"},
                {"name": "agent_type", "type": "tag"},
                {"name": "created_at", "type": "tag"},
                {
                    "name": "embedding",
                    "type": "vector",
                    "attrs": {
                        "algorithm": "flat",
                        "datatype": "float32",
                        "dims": EMBEDDING_DIMENSIONS,
                        "distance_metric": "cosine",
                    },
                },
            ],
        }
    )


def ensure_knowledge_index(settings: Settings | None = None) -> SearchIndex:
    if SearchIndex is None:  # pragma: no cover
        raise RuntimeError("redisvl is not installed. Run `pip install -e .` first.")

    settings = settings or get_settings()
    schema = build_knowledge_schema()
    index = SearchIndex(schema, redis_url=build_redis_url(settings))
    try:
        index.create()
    except Exception as exc:
        if "already exists" not in str(exc).lower():
            raise RuntimeError(f"Failed to create RedisVL index: {exc}") from exc
    return index


def _normalize_chunk(record: dict[str, Any]) -> dict[str, Any]:
    chunk = dict(record)
    metadata = chunk.get("metadata")
    if isinstance(metadata, str):
        try:
            chunk["metadata"] = json.loads(metadata)
        except json.JSONDecodeError:
            pass
    chunk.setdefault("source", "redis")
    return chunk


def upsert_knowledge_chunks(
    chunks: list[dict[str, Any]],
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    if not settings.has_redis_config:
        return {
            "ok": False,
            "stored": 0,
            "skipped": True,
            "message": "Redis is not configured; stored in local cache only.",
        }

    if not chunks:
        return {"ok": True, "stored": 0, "message": "No chunks to store"}

    index = ensure_knowledge_index(settings)
    records: list[dict[str, Any]] = []
    for chunk in chunks:
        record = dict(chunk)
        record["embedding"] = record.get("embedding") or embed_text(record["text"])
        records.append(record)

    index.load(records, id_field="id")
    return {"ok": True, "stored": len(records), "index": KNOWLEDGE_INDEX_NAME}


def search_knowledge_chunks(
    query: str,
    top_k: int = 5,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    settings = settings or get_settings()
    if not settings.has_redis_config:
        return []

    if SearchIndex is None or VectorQuery is None:  # pragma: no cover
        return []

    try:
        index = ensure_knowledge_index(settings)
        query_vector = embed_text(query)
        search_query = VectorQuery(
            vector=query_vector,
            vector_field_name="embedding",
            num_results=top_k,
        )
        raw_results = index.query(search_query)
    except Exception:
        return []

    normalized_results: list[dict[str, Any]] = []
    for item in raw_results or []:
        if isinstance(item, dict):
            normalized_results.append(_normalize_chunk(item))
            continue

        if hasattr(item, "model_dump"):
            normalized_results.append(_normalize_chunk(item.model_dump()))
            continue

        if hasattr(item, "__dict__"):
            normalized_results.append(_normalize_chunk(dict(item.__dict__)))

    return normalized_results[:top_k]
