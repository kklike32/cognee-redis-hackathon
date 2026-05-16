from sherlock.citations import build_citations


def test_build_citations_deduplicates_source_chunks():
    chunks = [
        {
            "source": "data/sources/gong_deel_transcript.md",
            "title": "Call Summary",
            "text": "Buyer asked about compliance ownership.",
            "metadata": {"chunk_index": 1, "heading_path": "Call Summary"},
        },
        {
            "source": "data/sources/gong_deel_transcript.md",
            "title": "Call Summary",
            "text": "Buyer asked about compliance ownership.",
            "metadata": {"chunk_index": 1, "heading_path": "Call Summary"},
        },
    ]

    citations = build_citations(chunks)

    assert len(citations) == 1
    assert citations[0]["id"] == "S1"
    assert citations[0]["source"] == "gong_deel_transcript.md"
