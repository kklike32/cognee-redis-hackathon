from sherlock.card_agent import generate_competitive_brief


def test_generate_competitive_brief_returns_cited_markdown_without_cache():
    result = generate_competitive_brief(
        competitor="deel",
        deal_context="Series A fintech expanding into Canada and the UK.",
        use_cache=False,
    )

    assert result["cache_status"] == "disabled"
    assert result["brief_markdown"]
    assert "Source citations" in result["brief_markdown"]
    assert result["sources"]
    assert result["model_used"] == "deterministic-fallback"


def test_generate_competitive_brief_rejects_non_deel():
    try:
        generate_competitive_brief("remote", "context", use_cache=False)
    except ValueError as exc:
        assert "Deel only" in str(exc)
    else:
        raise AssertionError("Expected non-Deel competitor to be rejected")
