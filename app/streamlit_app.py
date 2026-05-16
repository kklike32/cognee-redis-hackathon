from __future__ import annotations

import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st

from sherlock.markdown_store import read_battle_card
from sherlock.pending_changes import (
    approve_change,
    invalidate_competitor_cache,
    load_pending_changes,
    reject_change,
)

try:
    from app.redis_client import create_redis_client, ping_redis
except Exception:  # pragma: no cover - Streamlit should stay usable without deps.
    create_redis_client = None  # type: ignore[assignment]
    ping_redis = None  # type: ignore[assignment]


COMPETITORS = ["Deel"]
SOURCE_PATHS = [
    Path("data/sources/gong_deel_transcript.md"),
    Path("data/sources/g2_deel_review.md"),
    Path("data/sources/deel_product_launch.md"),
]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"


def _cache_key(competitor: str, deal_context: str, card: str) -> str:
    digest = hashlib.sha256(f"{deal_context}\n\n{card}".encode("utf-8")).hexdigest()[:24]
    return f"sherlock:brief:{_slug(competitor)}:{digest}"


def _get_redis_client():
    if create_redis_client is None:
        return None, "Redis client dependency is unavailable."
    try:
        client = create_redis_client()
        client.ping()
        return client, ""
    except Exception as exc:
        return None, str(exc)


def _load_source_snippets() -> list[dict[str, str]]:
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


def _extract_metadata(card: str) -> dict[str, str]:
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


def _section(card: str, heading: str) -> str:
    pattern = re.compile(
        rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)",
        re.MULTILINE,
    )
    match = pattern.search(card)
    return match.group(1).strip() if match else ""


def _generate_deterministic_brief(competitor: str, deal_context: str, card: str) -> str:
    strengths = _section(card, "Strengths to Acknowledge")
    weaknesses = _section(card, "Weaknesses to Attack")
    objections = _section(card, "Common Objections and Responses")
    questions = _section(card, "Trap-Setting Discovery Questions")
    recent_updates = _section(card, "Recent Analyst-Approved Updates")

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
"""


def generate_brief(competitor: str, deal_context: str) -> dict[str, Any]:
    started = time.perf_counter()
    card = read_battle_card()
    key = _cache_key(competitor, deal_context, card)
    client, redis_error = _get_redis_client()

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

    brief = _generate_deterministic_brief(competitor, deal_context, card)
    payload = {
        "brief": brief,
        "sources": _load_source_snippets(),
        "metadata": _extract_metadata(card),
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


def render_ae_view() -> None:
    st.subheader("AE View")
    competitor = st.selectbox("Competitor", COMPETITORS, index=0)
    deal_context = st.text_area(
        "Deal context",
        value=(
            "Series A fintech startup, 80 employees, expanding into Canada and the UK, "
            "currently evaluating Deel."
        ),
        height=120,
    )

    if st.button("Generate Brief", type="primary"):
        st.session_state["brief_payload"] = generate_brief(competitor, deal_context)

    payload = st.session_state.get("brief_payload")
    if not payload:
        st.info("Enter deal context and generate a brief.")
        return

    metric_cols = st.columns(3)
    metric_cols[0].metric("Cache", payload.get("cache_status", "unknown"))
    metric_cols[1].metric("Latency", f"{payload.get('latency_ms', 0)} ms")
    metric_cols[2].metric("Competitor", competitor)

    if payload.get("cache_status") == "no-cache":
        st.warning(f"Redis unavailable. Continuing in no-cache mode. {payload.get('redis_error', '')}")

    metadata = payload.get("metadata") or {}
    if metadata:
        st.markdown("### Battle Card Metadata")
        st.json(metadata)

    st.markdown("### Generated Brief")
    st.markdown(payload["brief"])

    st.markdown("### Sources / Citations")
    for source in payload.get("sources", []):
        st.markdown(f"- `{source['path']}` - {source['snippet']}")


def render_analyst_review() -> None:
    st.subheader("Analyst Review")
    changes = load_pending_changes()
    if not changes:
        st.info("No pending changes found. Run `python scripts/reset_demo.py` to restore demo data.")
        return

    for change in changes:
        with st.container(border=True):
            status = change.get("status", "pending")
            st.markdown(f"### {change.get('id', 'unknown')}")
            cols = st.columns(4)
            cols[0].markdown(f"**Competitor**  \n{change.get('competitor', '')}")
            cols[1].markdown(f"**Priority**  \n{change.get('priority', '')}")
            cols[2].markdown(f"**Section**  \n{change.get('proposed_section', '')}")
            cols[3].markdown(f"**Status**  \n{status}")
            st.markdown(f"**Source citation:** `{change.get('source_citation', '')}`")

            text_key = f"edit_{change['id']}"
            edited_text = st.text_area(
                "Proposed text",
                value=change.get("proposed_text", ""),
                key=text_key,
                height=140,
                disabled=status != "pending",
            )

            action_cols = st.columns([1, 1, 4])
            if action_cols[0].button("Approve", key=f"approve_{change['id']}", disabled=status != "pending"):
                approved = approve_change(change["id"], edited_text=edited_text)
                cache_result = invalidate_competitor_cache(str(approved.get("competitor", "Deel")))
                st.success(
                    f"Approved and appended to markdown. Cache invalidated: {cache_result.get('deleted', 0)} keys."
                )
                st.rerun()

            if action_cols[1].button("Reject", key=f"reject_{change['id']}", disabled=status != "pending"):
                reject_change(change["id"])
                st.warning("Rejected. Markdown was not changed.")
                st.rerun()


def main() -> None:
    st.set_page_config(page_title="Sherlock", page_icon="S", layout="wide")
    st.title("Sherlock")
    st.caption("Local-first competitive intelligence demo with AE briefs and analyst approval.")

    if ping_redis is not None:
        redis_status = ping_redis()
        if redis_status.get("ok"):
            st.sidebar.success("Redis connected")
        else:
            st.sidebar.warning("Redis unavailable; no-cache mode")
    else:
        st.sidebar.warning("Redis helpers unavailable; no-cache mode")

    st.sidebar.markdown("Reset demo state:")
    st.sidebar.code("python scripts/reset_demo.py", language="bash")

    ae_tab, analyst_tab = st.tabs(["AE View", "Analyst Review"])
    with ae_tab:
        render_ae_view()
    with analyst_tab:
        render_analyst_review()


if __name__ == "__main__":
    main()
