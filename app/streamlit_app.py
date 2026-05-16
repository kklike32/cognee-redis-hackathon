from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import streamlit as st

from sherlock.cache import invalidate_competitor_cache, redis_ping
from sherlock.card_agent import generate_competitive_brief
from sherlock.config import get_settings
from sherlock.ingest import ingest_demo_data
from sherlock.markdown_store import read_wiki, wiki_last_updated
from sherlock.pending_changes import approve_change, load_changes, reject_change, update_change_text
from sherlock.source_intake import ingest_source_file, ingest_source_text
from sherlock.wiki_builder import build_company_wiki


COMPETITOR = "deel"
UPLOAD_DIR = ROOT / ".cache" / "uploads"


def _save_upload(uploaded_file) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(uploaded_file.name).name
    path = UPLOAD_DIR / safe_name
    path.write_bytes(uploaded_file.getbuffer())
    return path


def _run_wiki_refresh() -> dict:
    wiki_result = build_company_wiki(company=COMPETITOR, use_llm=True)
    ingest_result = ingest_demo_data(get_settings())
    deleted = invalidate_competitor_cache(COMPETITOR, settings=get_settings())
    return {"wiki": wiki_result, "ingest": ingest_result, "cache_keys_invalidated": deleted}


def render_source_intake() -> None:
    st.subheader("1. Raw Source Intake")
    st.caption("Upload or paste Oyster-internal Deel evidence. No live web fetches or external source connectors run here.")

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("### Paste Source")
        title = st.text_input("Source title", value="Deel internal note")
        source_type = st.selectbox(
            "Source type",
            ["gong-style source", "g2-style source", "product launch source", "internal note"],
        )
        body = st.text_area("Source text", height=180)
        if st.button("Add Pasted Source", type="primary", use_container_width=True):
            try:
                result = ingest_source_text(title=title, body=body, source_type=source_type, company=COMPETITOR)
                st.success(f"Saved {result['path']}")
                st.json(result)
            except Exception as exc:
                st.error(str(exc))

    with right:
        st.markdown("### Upload Source")
        uploaded = st.file_uploader("Supported: .md, .txt, .html, .htm, .pdf", type=["md", "txt", "html", "htm", "pdf"])
        if st.button("Add Uploaded Source", use_container_width=True):
            if uploaded is None:
                st.warning("Choose a file first.")
            else:
                try:
                    saved = _save_upload(uploaded)
                    result = ingest_source_file(saved, company=COMPETITOR)
                    st.success(f"Saved {result['path']}")
                    st.json(result)
                except Exception as exc:
                    st.error(str(exc))

    st.divider()
    if st.button("Rebuild Wiki + Local Index", use_container_width=True):
        try:
            result = _run_wiki_refresh()
            st.session_state["last_wiki_refresh"] = result
            st.success(
                "Knowledge wiki rebuilt, local chunks refreshed, and cached Deel briefs invalidated."
            )
        except Exception as exc:
            st.error(str(exc))

    if "last_wiki_refresh" in st.session_state:
        st.markdown("### Last Refresh")
        st.json(st.session_state["last_wiki_refresh"])


def render_knowledge_wiki() -> None:
    st.subheader("2. LLM Knowledge Wiki")
    st.caption("Canonical Oyster-internal Deel knowledge. Redis caches generated briefs; Cognee is optional local indexing.")

    settings = get_settings()
    redis_status = redis_ping(settings)
    cols = st.columns(4)
    cols[0].metric("Company", "Deel")
    cols[1].metric("Audience", "Oyster internal")
    cols[2].metric("Redis", "Connected" if redis_status["ok"] else "Unavailable")
    cols[3].metric("Last wiki update", wiki_last_updated(COMPETITOR, settings=settings))

    if st.button("Build Knowledge Wiki", type="primary"):
        try:
            result = _run_wiki_refresh()
            st.session_state["last_wiki_refresh"] = result
            st.success(
                f"Wiki built with {result['wiki']['generation_mode']}; Cognee status: {result['wiki']['cognee_status']}."
            )
        except Exception as exc:
            st.error(str(exc))

    if "last_wiki_refresh" in st.session_state:
        result = st.session_state["last_wiki_refresh"]
        summary = st.columns(4)
        summary[0].metric("Generation", result["wiki"]["generation_mode"])
        summary[1].metric("Cognee", result["wiki"]["cognee_status"])
        summary[2].metric("Sources", len(result["wiki"]["sources"]))
        summary[3].metric("Invalidated", result["cache_keys_invalidated"])

    with st.expander("data/wiki/deel.md", expanded=True):
        st.markdown(read_wiki(COMPETITOR, settings=settings))


def render_battle_card() -> None:
    st.subheader("3. Battle Card Agent")
    st.caption("Deal-specific AE brief generated from the knowledge wiki plus cited source context.")

    default_context = (
        "Series A fintech startup with 80 employees, expanding into Canada and the UK, "
        "currently evaluating Deel. They care about onboarding speed, compliance confidence, "
        "and predictable pricing."
    )
    deal_context = st.text_area("Deal context", value=default_context, height=140)

    if st.button("Generate Deel Brief", type="primary", use_container_width=True):
        st.session_state["brief_payload"] = generate_competitive_brief(
            competitor=COMPETITOR,
            deal_context=deal_context,
            use_cache=True,
            settings=get_settings(),
        )

    payload = st.session_state.get("brief_payload")
    if not payload:
        st.info("Generate a brief to see cache, retrieval, and citations.")
        return

    cols = st.columns(5)
    cols[0].metric("Cache", payload["cache_status"])
    cols[1].metric("Latency", f"{payload['latency_ms']} ms")
    cols[2].metric("Model", payload["model_used"])
    cols[3].metric("Cognee", payload.get("retrieval_status", {}).get("cognee", "unknown"))
    cols[4].metric("Local index", payload.get("retrieval_status", {}).get("local_index", "unknown"))

    st.markdown(payload["brief_markdown"])

    with st.expander("Source provenance", expanded=False):
        for source in payload.get("sources", []):
            st.markdown(
                f"- **[{source['id']}] {source['source']}** ({source.get('source_type')}) "
                f"{source.get('heading', '')}: {source.get('snippet', '')}"
            )


def render_analyst_review() -> None:
    st.subheader("Analyst Review")
    st.caption("Human approval updates the knowledge wiki and invalidates cached Deel briefs.")

    settings = get_settings()
    changes = load_changes(settings)
    pending = [change for change in changes if change.get("status") == "pending"]
    resolved = [change for change in changes if change.get("status") != "pending"]

    if not pending:
        st.info("No pending changes. Run `python3 scripts/reset_demo.py` to restore the demo queue.")

    for change in pending:
        with st.container(border=True):
            st.caption(change["id"])
            st.markdown(f"### {change.get('title', 'Pending change')}")
            st.write(change.get("rationale", ""))
            st.write(f"Target: `{change.get('target_section', '')}`")
            edited = st.text_area(
                "Proposed markdown",
                value=change.get("proposed_markdown", ""),
                key=f"edit-{change['id']}",
                height=130,
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
                st.session_state.pop("brief_payload", None)
                st.rerun()
            if actions[2].button("Reject", key=f"reject-{change['id']}"):
                reject_change(change["id"], settings=settings)
                st.warning("Rejected.")
                st.rerun()
            actions[3].caption("Approval writes to `data/wiki/deel.md` and clears cached Deel briefs.")

    if resolved:
        st.divider()
        st.caption("Resolved changes")
        for change in resolved:
            st.write(f"`{change['status']}` - {change.get('title', change['id'])}")


def main() -> None:
    st.set_page_config(page_title="Sherlock", page_icon="S", layout="wide")
    st.title("Sherlock")
    st.caption("Local-first Oyster-internal competitive intelligence for Deel. No Cognee Cloud, Redis Cloud, CRM, Gong, or G2 live integrations.")

    redis_status = redis_ping(get_settings())
    st.sidebar.metric("Redis", "Connected" if redis_status["ok"] else "Unavailable")
    st.sidebar.caption(redis_status["message"])
    st.sidebar.markdown("Demo reset:")
    st.sidebar.code("python3 scripts/reset_demo.py", language="bash")

    source_tab, wiki_tab, battle_tab, analyst_tab = st.tabs(
        ["1. Source Intake", "2. Knowledge Wiki", "3. Battle Card", "Analyst Review"]
    )
    with source_tab:
        render_source_intake()
    with wiki_tab:
        render_knowledge_wiki()
    with battle_tab:
        render_battle_card()
    with analyst_tab:
        render_analyst_review()


if __name__ == "__main__":
    main()
