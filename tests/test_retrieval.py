from sherlock.config import get_settings
from sherlock.ingest import ingest_demo_data
from sherlock.retrieval import retrieve_context


def test_retrieve_context_returns_cited_chunks():
    settings = get_settings()
    ingest_demo_data(settings)

    chunks = retrieve_context("Series A buyer compliance objections", "deel", top_k=2, settings=settings)

    assert len(chunks) == 2
    assert {"source_id", "title", "text", "citation_label", "source_path"} <= set(chunks[0])
    assert chunks[0]["citation_label"] == "S1"
