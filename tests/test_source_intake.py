from __future__ import annotations

from pathlib import Path

import pytest

from sherlock import source_intake
from sherlock.source_intake import ingest_source_file, ingest_source_text


def test_ingest_source_text_writes_normalized_deel_record(tmp_path, monkeypatch):
    monkeypatch.setattr(source_intake, "SOURCES_DIR", tmp_path)

    result = ingest_source_text(
        "Deel Launch Notes!",
        "  Deel launched   workflow automation.\n\n\nSales teams should track it. ",
        "note",
        company=" Deel ",
    )

    stored_path = Path(result["path"])
    stored = stored_path.read_text(encoding="utf-8")
    assert result["ok"] is True
    assert stored_path.parent == tmp_path
    assert stored_path.name.startswith("deel-launch-notes-")
    assert result["title"] == "Deel Launch Notes!"
    assert result["source_type"] == "note"
    assert result["company"] == "deel"
    assert result["bytes"] > 0
    assert result["text_length"] == len("Deel launched workflow automation.\nSales teams should track it.")
    assert len(result["content_hash"]) == 64
    assert "company: deel" in stored
    assert "Deel launched workflow automation." in stored


def test_ingest_source_text_rejects_non_deel_company(tmp_path, monkeypatch):
    monkeypatch.setattr(source_intake, "SOURCES_DIR", tmp_path)

    with pytest.raises(ValueError, match="Only Deel"):
        ingest_source_text("Competitor", "Body", "note", company="remote")


def test_ingest_markdown_file(tmp_path, monkeypatch):
    monkeypatch.setattr(source_intake, "SOURCES_DIR", tmp_path / "sources")
    source = tmp_path / "Deel Product.md"
    source.write_text("# Deel Product\n\n- New payroll workflow\n", encoding="utf-8")

    result = ingest_source_file(source)

    stored = Path(result["path"]).read_text(encoding="utf-8")
    assert result["title"] == "Deel Product"
    assert result["source_type"] == "md"
    assert result["company"] == "deel"
    assert result["text_length"] == len("# Deel Product\n- New payroll workflow")
    assert "# Deel Product" in stored
    assert "New payroll workflow" in stored


def test_ingest_text_file(tmp_path, monkeypatch):
    monkeypatch.setattr(source_intake, "SOURCES_DIR", tmp_path / "sources")
    source = tmp_path / "deel-review.txt"
    source.write_text(" Deel support response improved. \n", encoding="utf-8")

    result = ingest_source_file(source, company="DEEL")

    assert result["title"] == "deel-review"
    assert result["source_type"] == "txt"
    assert result["company"] == "deel"
    assert result["text_length"] == len("Deel support response improved.")


def test_ingest_html_file_extracts_readable_text_and_title(tmp_path, monkeypatch):
    monkeypatch.setattr(source_intake, "SOURCES_DIR", tmp_path / "sources")
    source = tmp_path / "page.html"
    source.write_text(
        """
        <html>
          <head>
            <title>Deel HTML Brief</title>
            <style>.hidden { display: none; }</style>
          </head>
          <body>
            <h1>Deel Brief</h1>
            <script>ignoreMe()</script>
            <p>Readable launch detail.</p>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    result = ingest_source_file(source)

    stored = Path(result["path"]).read_text(encoding="utf-8")
    assert result["title"] == "Deel HTML Brief"
    assert result["source_type"] == "html"
    assert "Deel Brief" in stored
    assert "Readable launch detail." in stored
    assert "ignoreMe" not in stored
    assert "display: none" not in stored


def test_ingest_pdf_reports_missing_dependency_or_success(tmp_path, monkeypatch):
    monkeypatch.setattr(source_intake, "SOURCES_DIR", tmp_path / "sources")
    monkeypatch.setattr(source_intake.util, "find_spec", lambda name: None)
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4\nnot a complete pdf\n")

    with pytest.raises(ValueError, match="PDF source intake requires"):
        ingest_source_file(source)
