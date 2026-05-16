from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.reset_demo import reset_demo
from sherlock.cache import redis_ping
from sherlock.card_agent import generate_competitive_brief
from sherlock.config import get_settings
from sherlock.ingest import ingest_demo_data
from sherlock.markdown_store import read_wiki
from sherlock.pending_changes import approve_change, pending_only, reject_change, update_change_text
from sherlock.pending_generator import generate_pending_from_wiki
from sherlock.source_intake import ingest_source_file, ingest_source_text
from sherlock.wiki_builder import build_company_wiki


def _json_panel(value: object) -> None:
    st.code(json.dumps(value, indent=2), language="json")


def _source_intake_tab() -> None:
    st.subheader("1. Source Intake")
    st.caption("Add internal sources from pasted notes or uploaded files.")

    with st.form("paste_source_form"):
        title = st.text_input("Title", value="Internal call note")
        source_type = st.selectbox("Source type", ["gong-style source", "g2-style source", "product launch source", "other"]) 
        body = st.text_area("Source text", height=180)
        submitted = st.form_submit_button("Ingest pasted source")
        if submitted:
            try:
                result = ingest_source_text(title=title, body=body, source_type=source_type, company="deel")
                st.success("Source ingested.")
                _json_panel(result)
            except Exception as exc:
                st.error(str(exc))

    st.markdown("---")

    uploads = st.file_uploader(
        "Upload files",
        type=["md", "txt", "html", "htm", "pdf"],
        accept_multiple_files=True,
    )
    if st.button("Ingest uploaded files", use_container_width=True):
        if not uploads:
            st.warning("Select at least one file to ingest.")
        else:
            results = []
            for upload in uploads:
                suffix = Path(upload.name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as handle:
                    handle.write(upload.getbuffer())
                    temp_path = Path(handle.name)
                try:
                    results.append(ingest_source_file(temp_path, company="deel"))
                except Exception as exc:
                    results.append({"ok": False, "file": upload.name, "error": str(exc)})
                finally:
                    try:
                        temp_path.unlink(missing_ok=True)
                    except Exception:
                        pass
            st.success("Upload ingestion complete.")
            _json_panel(results)


def _knowledge_wiki_tab() -> None:
    st.subheader("2. Knowledge Wiki")
    st.caption("Build or rebuild the local Deel wiki from local sources.")

    use_llm = st.checkbox("Allow optional LLM synthesis", value=True)
    if st.button("Build wiki", use_container_width=True):
        with st.spinner("Building wiki..."):
            try:
                result = build_company_wiki(company="deel", use_llm=use_llm)
                st.success("Wiki built.")
                st.metric("Generation mode", result.get("generation_mode", "unknown"))
                st.metric("Cognee status", result.get("cognee_status", "unknown"))
                st.metric("Latency (ms)", int(result.get("latency_ms", 0)))
                st.markdown("### Wiki markdown")
                st.markdown(result.get("wiki_markdown", ""))
                st.markdown("### Source summary")
                _json_panel(result.get("sources", []))
            except Exception as exc:
                st.error(str(exc))

    st.markdown("### Current wiki")
    try:
        st.markdown(read_wiki("deel"))
    except Exception as exc:
        st.info(f"Wiki is not available yet: {exc}")


def _battle_card_tab(settings) -> None:
    st.subheader("3. Battle Card")
    st.caption("Generate a cited, deal-specific Oyster vs Deel brief.")

    default_context = (
        "Series A fintech startup with 80 employees, expanding into Canada and the UK, "
        "currently evaluating Deel. They care about onboarding speed, compliance confidence, "
        "and predictable pricing."
    )
    deal_context = st.text_area("Deal context", value=default_context, height=140)
    use_cache = st.checkbox("Use Redis cache", value=True)

    if st.button("Generate brief", use_container_width=True):
        with st.spinner("Generating brief..."):
            try:
                result = generate_competitive_brief(
                    competitor="deel",
                    deal_context=deal_context,
                    use_cache=use_cache,
                    settings=settings,
                )
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Cache", str(result.get("cache_status", "unknown")))
                m2.metric("Latency (ms)", int(result.get("latency_ms", 0)))
                m3.metric("Model", str(result.get("model_used", "deterministic-fallback")))
                retrieval = result.get("retrieval_status", {})
                m4.metric("Cognee retrieval", str(retrieval.get("cognee", "unknown")))

                st.markdown("### Brief")
                st.markdown(result.get("brief_markdown", ""))
                st.markdown("### Retrieval status")
                _json_panel(retrieval)
                st.markdown("### Citations")
                _json_panel(result.get("sources", []))
            except Exception as exc:
                st.error(str(exc))


def _analyst_review_tab(settings) -> None:
    st.subheader("4. Analyst Review")
    st.caption("Review pending proposals and approve, edit, or reject changes.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("Generate pending proposals", use_container_width=True):
            try:
                result = generate_pending_from_wiki(competitor="deel", persist=True)
                st.success("Pending proposals generated.")
                _json_panel(result)
            except Exception as exc:
                st.error(str(exc))
    with c2:
        if st.button("Refresh pending list", use_container_width=True):
            st.rerun()

    changes = pending_only(settings=settings)
    if not changes:
        st.info("No pending changes.")
        return

    options = {f"{c.get('id')} | {c.get('priority')} | {c.get('proposed_section')}": c for c in changes}
    selected = st.selectbox("Pending change", list(options.keys()))
    change = options[selected]

    st.markdown("### Change metadata")
    _json_panel(
        {
            "id": change.get("id"),
            "priority": change.get("priority"),
            "proposed_section": change.get("proposed_section"),
            "source_citation": change.get("source_citation"),
            "status": change.get("status"),
        }
    )

    current_text = change.get("proposed_markdown") or change.get("proposed_text") or ""
    edited_text = st.text_area("Edited markdown", value=current_text, height=220, key=f"edit_{change.get('id')}")

    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button("Save draft", use_container_width=True):
            try:
                update_change_text(str(change.get("id")), edited_text, settings=settings)
                st.success("Draft saved.")
            except Exception as exc:
                st.error(str(exc))
    with a2:
        if st.button("Approve", use_container_width=True):
            try:
                approved = approve_change(str(change.get("id")), edited_markdown=edited_text, settings=settings)
                st.success("Change approved.")
                _json_panel(approved)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    with a3:
        if st.button("Reject", use_container_width=True):
            try:
                rejected = reject_change(str(change.get("id")), settings=settings)
                st.warning("Change rejected.")
                _json_panel(rejected)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def main() -> None:
    st.set_page_config(page_title="Sherlock Demo", page_icon="🕵️", layout="wide")
    st.title("Sherlock: Local Competitive Intelligence Demo")

    settings = get_settings()
    redis_status = redis_ping(settings=settings)

    with st.sidebar:
        st.header("Environment")
        st.write(f"Company scope: {settings.default_company}")
        st.write(f"Redis URL: {settings.redis_url}")
        st.write(f"LLM model: {settings.llm_model}")
        st.write(f"Redis status: {'ok' if redis_status.get('ok') else 'not available'}")
        if st.button("Reset demo state", use_container_width=True):
            try:
                st.success("Demo reset complete.")
                _json_panel(reset_demo())
            except Exception as exc:
                st.error(str(exc))
        if st.button("Ingest demo data", use_container_width=True):
            try:
                st.success("Demo data ingested.")
                _json_panel(ingest_demo_data(settings=settings))
            except Exception as exc:
                st.error(str(exc))

    tabs = st.tabs(["Source Intake", "Knowledge Wiki", "Battle Card", "Analyst Review"])
    with tabs[0]:
        _source_intake_tab()
    with tabs[1]:
        _knowledge_wiki_tab()
    with tabs[2]:
        _battle_card_tab(settings)
    with tabs[3]:
        _analyst_review_tab(settings)


if __name__ == "__main__":
    main()
