from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

from sherlock.cache import redis_ping
from sherlock.card_agent import generate_brief
from sherlock.config import get_settings
from sherlock.markdown_store import read_wiki
from sherlock.pending_changes import approve_change, load_changes, reject_change, update_change_text


st.set_page_config(page_title="Sherlock", page_icon="S", layout="wide")

st.markdown(
    """
    <style>
      .main .block-container { padding-top: 1.5rem; max-width: 1180px; }
      div[data-testid="stMetricValue"] { font-size: 1.35rem; }
      .sherlock-header {
        border-bottom: 1px solid #e5e7eb;
        padding-bottom: 0.8rem;
        margin-bottom: 1rem;
      }
      .sherlock-muted { color: #6b7280; font-size: 0.9rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

settings = get_settings()
redis_status = redis_ping(settings)

st.markdown(
    """
    <div class="sherlock-header">
      <h1 style="margin-bottom:0.15rem;">Sherlock</h1>
      <div class="sherlock-muted">Local-first competitive intelligence wiki for Oyster HR battle cards</div>
    </div>
    """,
    unsafe_allow_html=True,
)

top_cols = st.columns([1, 1, 2])
top_cols[0].metric("Competitor", "Deel")
top_cols[1].metric("Redis", "Connected" if redis_status["ok"] else "Unavailable")
top_cols[2].caption(redis_status["message"])

ae_tab, analyst_tab = st.tabs(["AE View", "Analyst Review"])

with ae_tab:
    left, right = st.columns([0.95, 1.25], gap="large")
    with left:
        st.subheader("Deal Context")
        competitor = st.selectbox("Competitor", ["deel"], format_func=lambda value: value.title())
        default_context = (
            "Series A fintech startup, 80 employees, expanding into Canada and the UK, "
            "currently evaluating Deel."
        )
        deal_context = st.text_area("Context", value=default_context, height=160)
        generate = st.button("Generate Brief", type="primary", use_container_width=True)
        st.divider()
        st.caption("Canonical markdown preview")
        with st.expander("data/wiki/deel.md", expanded=False):
            st.markdown(read_wiki("deel", settings))

    with right:
        if generate or "last_brief" not in st.session_state:
            st.session_state.last_brief = generate_brief(
                competitor=competitor,
                deal_context=deal_context,
                settings=settings,
            ).as_dict()
        brief = st.session_state.last_brief
        metrics = st.columns(3)
        metrics[0].metric("Cache", brief["cache_status"])
        metrics[1].metric("Latency", f"{brief['latency_ms']} ms")
        cognee_state = brief.get("retrieval_status", {}).get("cognee", "unknown")
        metrics[2].metric("Cognee", cognee_state)
        st.markdown(brief["markdown"])

with analyst_tab:
    st.subheader("Pending Battle Card Changes")
    changes = load_changes(settings)
    pending = [change for change in changes if change.get("status") == "pending"]
    resolved = [change for change in changes if change.get("status") != "pending"]

    if not pending:
        st.info("No pending changes. Run `python3 scripts/reset_demo.py` to restore the demo queue.")
    for change in pending:
        with st.container(border=True):
            st.caption(change["id"])
            st.markdown(f"### {change['title']}")
            st.write(change["rationale"])
            st.write(f"Target: `{change['target_section']}`")
            edited = st.text_area(
                "Proposed markdown",
                value=change["proposed_markdown"],
                key=f"edit-{change['id']}",
                height=150,
            )
            actions = st.columns([1, 1, 1, 2])
            if actions[0].button("Save Edit", key=f"save-{change['id']}"):
                update_change_text(change["id"], edited, settings=settings)
                st.success("Edit saved.")
                st.rerun()
            if actions[1].button("Approve", type="primary", key=f"approve-{change['id']}"):
                result = approve_change(change["id"], edited_markdown=edited, settings=settings)
                st.success(
                    f"Approved. Invalidated {result.get('cache_keys_invalidated', 0)} Redis cache keys."
                )
                st.session_state.pop("last_brief", None)
                st.rerun()
            if actions[2].button("Reject", key=f"reject-{change['id']}"):
                reject_change(change["id"], settings=settings)
                st.warning("Rejected.")
                st.rerun()
            actions[3].caption("Approval updates markdown and invalidates cached Deel briefs.")

    if resolved:
        st.divider()
        st.caption("Resolved changes")
        for change in resolved:
            st.write(f"`{change['status']}` - {change['title']}")
