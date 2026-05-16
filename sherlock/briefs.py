from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

from .markdown_store import read_battle_card

SOURCE_PATHS = [
    Path("data/sources/gong_deel_transcript.md"),
    Path("data/sources/g2_deel_review.md"),
    Path("data/sources/deel_product_launch.md"),
    Path("data/incoming/wiki_update_deel.md"),
]


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"


def brief_cache_key(competitor: str, deal_context: str, card: str) -> str:
    digest = hashlib.sha256(f"{deal_context}\n\n{card}".encode("utf-8")).hexdigest()[:24]
    return f"sherlock:brief:{slug(competitor)}:{digest}"


def get_redis_client():
    try:
        from app.redis_client import create_redis_client

        client = create_redis_client()
        client.ping()
        return client, ""
    except Exception as exc:
        return None, str(exc)


def load_source_snippets() -> list[dict[str, str]]:
    snippets: list[dict[str, str]] = []
    for path in SOURCE_PATHS:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8").strip()
        first_lines = [line.strip("- ") for line in text.splitlines() if line.strip()][:5]
        snippets.append(
            {
                "path": str(path),
                "title": first_lines[0].lstrip("# ").strip() if first_lines else path.stem,
                "snippet": " ".join(first_lines[1:4]),
            }
        )
    return snippets


def extract_metadata(card: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    in_metadata = False
    for line in card.splitlines():
        if line.strip() == "## Metadata":
            in_metadata = True
            continue
        if in_metadata and line.startswith("## "):
            break
        if in_metadata and line.strip().startswith("- ") and ":" in line:
            key, value = line.strip()[2:].split(":", 1)
            metadata[key.strip()] = value.strip()
    return metadata


def section(card: str, heading: str) -> str:
    pattern = re.compile(
        rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)",
        re.MULTILINE,
    )
    match = pattern.search(card)
    return match.group(1).strip() if match else ""


def generate_deterministic_brief(competitor: str, deal_context: str, card: str) -> str:
    strengths = section(card, "Strengths to Acknowledge")
    weaknesses = section(card, "Weaknesses to Attack")
    objections = section(card, "Common Objections and Responses")
    questions = section(card, "Trap-Setting Discovery Questions")
    recent_updates = section(card, "Recent Analyst-Approved Updates")

    context = deal_context.strip() or "No specific deal context provided."
    approved_updates = (
        f"\n\n## Analyst-Approved Freshness\n{recent_updates}"
        if recent_updates
        else ""
    )

    return f"""# Sherlock AE Brief: {competitor}

## Deal Context
{context}

## Recommended Talk Track
Lead with implementation confidence and compliance clarity. Acknowledge {competitor}'s brand, then move the buyer from "who is bigger" to "who will help this lean team avoid mistakes in the first 90 days."

## Strengths to Acknowledge
{strengths or "- Brand recognition and breadth are credible strengths."}

## Weaknesses to Attack
{weaknesses or "- Press on support consistency and country-specific guidance."}

## Objections and Responses
{objections or "- Reframe speed around safe implementation, not just fast signature."}

## Trap-Setting Questions
{questions or "- Who owns local compliance decisions after contract signature?"}
{approved_updates}

## Sources Used
- `data/wiki/deel.md`
- `data/sources/gong_deel_transcript.md`
- `data/sources/g2_deel_review.md`
- `data/sources/deel_product_launch.md`
- `data/incoming/wiki_update_deel.md`
"""


def generate_brief(competitor: str, deal_context: str) -> dict[str, Any]:
    started = time.perf_counter()
    card = read_battle_card()
    key = brief_cache_key(competitor, deal_context, card)
    client, redis_error = get_redis_client()

    if client is not None:
        try:
            cached = client.get(key)
            if cached:
                payload = json.loads(cached)
                payload["cache_status"] = "hit"
                payload["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
                return payload
        except Exception as exc:
            redis_error = str(exc)
            client = None

    payload = {
        "brief": generate_deterministic_brief(competitor, deal_context, card),
        "sources": load_source_snippets(),
        "metadata": extract_metadata(card),
        "cache_status": "miss" if client is not None else "no-cache",
        "cache_key": key,
        "redis_error": redis_error,
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
    }

    if client is not None:
        try:
            client.setex(key, 3600, json.dumps(payload))
        except Exception as exc:
            payload["cache_status"] = "no-cache"
            payload["redis_error"] = str(exc)

    return payload
