from __future__ import annotations

import pytest

from sherlock import wiki_builder


def test_build_company_wiki_deterministic_without_llm_key(tmp_path, monkeypatch):
    sources_dir = tmp_path / "data" / "sources"
    wiki_dir = tmp_path / "data" / "wiki"
    sources_dir.mkdir(parents=True)

    (sources_dir / "gong_deel_transcript.md").write_text(
        """# Synthetic Gong Transcript: Deel Competitive Deal

## Notes

- Prospect has 80 employees and plans to hire in Canada and the UK this quarter.
- Buyer likes Deel's brand recognition but is unsure how much compliance support they will receive after implementation.
- The people team has two operators and no dedicated in-house employment counsel.
""",
        encoding="utf-8",
    )
    (sources_dir / "g2_deel_review.md").write_text(
        """# Synthetic G2 Review Signal: Deel

## Summary

- Positive signal: broad platform and fast setup are commonly valued.
- Risk signal: lean teams care deeply about support responsiveness when edge cases appear.
""",
        encoding="utf-8",
    )
    (sources_dir / "deel_product_launch.md").write_text(
        """# Synthetic Product Launch Note: Deel

## Summary

Deel announced new workflow automation capabilities aimed at helping teams manage more HR operations in one place.

## Sales Interpretation

Reframe toward whether the buyer needs more automation, or more guided help with the first risky international hires.
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(wiki_builder, "SOURCES_DIR", sources_dir)
    monkeypatch.setattr(wiki_builder, "WIKI_DIR", wiki_dir)
    monkeypatch.setattr(wiki_builder, "DEEL_WIKI_PATH", wiki_dir / "deel.md")
    monkeypatch.delenv("SHERLOCK_USE_LLM", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("SHERLOCK_INDEX_COGNEE", raising=False)

    result = wiki_builder.build_company_wiki()

    assert result["generation_mode"] == "deterministic-fallback"
    assert result["cognee_status"] in {"indexed", "added_not_cognified", "missing", "error"}
    assert result["sources"]
    assert "wiki_markdown" in result
    assert result["wiki_markdown"] == (wiki_dir / "deel.md").read_text(encoding="utf-8")
    assert "# Deel Battle Card" in result["wiki_markdown"]
    for heading in wiki_builder.BATTLE_CARD_HEADINGS:
        assert f"## {heading}" in result["wiki_markdown"]
    assert "gong_deel_transcript.md line" in result["wiki_markdown"]
    assert "Buyer likes Deel's brand recognition" in result["wiki_markdown"]


def test_build_company_wiki_rejects_non_deel():
    with pytest.raises(ValueError, match="Only company='deel' is supported"):
        wiki_builder.build_company_wiki(company="oyster")
