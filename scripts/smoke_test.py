from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.reset_demo import reset_demo
from sherlock.cache import invalidate_competitor_cache, redis_ping
from sherlock.card_agent import generate_brief
from sherlock.config import get_settings
from sherlock.ingest import ingest_demo_data
from sherlock.markdown_store import read_wiki
from sherlock.pending_changes import approve_change, pending_only
from sherlock.retrieval import retrieve_context


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> dict:
    settings = get_settings()
    reset_demo()

    import streamlit  # noqa: F401

    redis_status = redis_ping(settings)
    check(redis_status["ok"], redis_status["message"])

    ingest_result = ingest_demo_data(settings)
    check(ingest_result["chunks"] > 0, "Ingestion produced no chunks")
    retrieved = retrieve_context("Series A buyer compliance objections", "deel", top_k=2, settings=settings)
    check(len(retrieved) >= 2, "Retrieval returned fewer than 2 chunks")
    check(retrieved[0].get("citation_label"), "Retrieved chunks are missing citation labels")

    context = (
        "Series A fintech startup, 80 employees, expanding into Canada and the UK, "
        "currently evaluating Deel."
    )
    first = generate_brief("deel", context, settings=settings)
    check(first.citations, "Brief did not include citations")
    second = generate_brief("deel", context, settings=settings)
    check(second.cache_status == "hit", f"Expected cache hit, got {second.cache_status}")

    changes = pending_only(settings)
    check(changes, "No pending changes found")
    approved = approve_change(changes[0]["id"], settings=settings)
    updated_wiki = read_wiki("deel", settings=settings)
    check("sherlock-approved" in updated_wiki, "Approval did not update markdown")
    check(
        int(approved.get("cache_keys_invalidated", 0)) >= 1,
        "Approval did not invalidate Redis cache keys",
    )

    invalidate_competitor_cache("deel", settings=settings)
    reset_demo()
    return {
        "ok": True,
        "redis": redis_status,
        "ingested_chunks": ingest_result["chunks"],
        "retrieved_chunks": len(retrieved),
        "first_cache_status": first.cache_status,
        "second_cache_status": second.cache_status,
        "approval_status": approved["status"],
    }


if __name__ == "__main__":
    print(json.dumps(main(), indent=2))
