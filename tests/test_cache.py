from pathlib import Path

from sherlock.cache import build_cache_key, delete_by_prefix


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


def test_delete_by_prefix_handles_missing_redis():
    assert delete_by_prefix("sherlock:test:", settings=None) >= 0
