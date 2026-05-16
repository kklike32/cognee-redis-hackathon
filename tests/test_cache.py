from pathlib import Path

from sherlock.cache import build_cache_key


def test_cache_key_changes_with_wiki_hash(tmp_path):
    wiki = tmp_path / "deel.md"
    source = tmp_path / "source.md"
    wiki.write_text("one", encoding="utf-8")
    source.write_text("source", encoding="utf-8")

    first = build_cache_key("deel", "context", wiki, [source])
    wiki.write_text("two", encoding="utf-8")
    second = build_cache_key("deel", "context", wiki, [source])

    assert first != second
    assert first.startswith("sherlock:brief:v1:deel:")
