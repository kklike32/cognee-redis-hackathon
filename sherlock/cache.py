from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import Settings, get_settings

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None  # type: ignore[assignment]


PROMPT_VERSION = "sherlock-card-v1"
CACHE_PREFIX = "sherlock:brief:v1"


@dataclass(frozen=True)
class CacheLookup:
    status: str
    key: str
    value: dict[str, Any] | None = None
    message: str = ""


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def file_hash(path: Path) -> str:
    if not path.exists():
        return "missing"
    return _sha(path.read_text(encoding="utf-8"))


def sources_hash(paths: list[Path]) -> str:
    payload = []
    for path in sorted(paths):
        payload.append(f"{path.name}:{file_hash(path)}")
    return _sha("|".join(payload))


def redis_client(settings: Settings | None = None):
    settings = settings or get_settings()
    if redis is None:
        return None
    try:
        return redis.Redis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        return None


def redis_ping(settings: Settings | None = None) -> dict[str, Any]:
    client = redis_client(settings)
    if client is None:
        return {"ok": False, "message": "redis package is missing or Redis URL is invalid"}
    try:
        return {"ok": bool(client.ping()), "message": "Redis ping succeeded"}
    except Exception as exc:
        return {"ok": False, "message": f"Redis ping failed: {exc}"}


def build_cache_key(
    competitor: str,
    deal_context: str,
    wiki_path: Path,
    source_paths: list[Path],
) -> str:
    key_payload = {
        "competitor": competitor.lower(),
        "deal_context": deal_context.strip(),
        "prompt_version": PROMPT_VERSION,
        "wiki_hash": file_hash(wiki_path),
        "sources_hash": sources_hash(source_paths),
    }
    return f"{CACHE_PREFIX}:{competitor.lower()}:{_sha(json.dumps(key_payload, sort_keys=True))}"


def get_cached_brief(key: str, settings: Settings | None = None) -> CacheLookup:
    client = redis_client(settings)
    if client is None:
        return CacheLookup(status="unavailable", key=key, message="Redis client unavailable")
    try:
        raw = client.get(key)
    except Exception as exc:
        return CacheLookup(status="unavailable", key=key, message=str(exc))
    if not raw:
        return CacheLookup(status="miss", key=key)
    try:
        return CacheLookup(status="hit", key=key, value=json.loads(raw))
    except json.JSONDecodeError:
        return CacheLookup(status="miss", key=key, message="Cached payload was invalid JSON")


def set_cached_brief(key: str, value: dict[str, Any], settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    client = redis_client(settings)
    if client is None:
        return False
    try:
        client.setex(key, settings.cache_ttl_seconds, json.dumps(value))
        return True
    except Exception:
        return False


def delete_by_prefix(prefix: str, settings: Settings | None = None) -> int:
    client = redis_client(settings)
    if client is None:
        return 0
    deleted = 0
    try:
        pattern = prefix if prefix.endswith("*") else f"{prefix}*"
        for key in client.scan_iter(match=pattern):
            deleted += int(client.delete(key))
    except Exception:
        return deleted
    return deleted


def invalidate_competitor_cache(competitor: str, settings: Settings | None = None) -> int:
    return delete_by_prefix(f"{CACHE_PREFIX}:{competitor.lower()}:", settings=settings)


def clear_demo_redis_keys(settings: Settings | None = None) -> int:
    patterns = ["sherlock:*", "founderos:knowledge*", "idx:founderos-knowledge*"]
    deleted = 0
    for pattern in patterns:
        deleted += delete_by_prefix(pattern, settings=settings)
    client = redis_client(settings)
    if client is None:
        return deleted
    try:
        client.execute_command("FT.DROPINDEX", "founderos-knowledge", "DD")
    except Exception:
        pass
    return deleted
