from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from importlib import import_module, util
from pathlib import Path
from typing import Any

SOURCES_DIR = Path("data") / "sources"
SUPPORTED_TEXT_SUFFIXES = {".md", ".txt", ".html", ".htm"}


class _ReadableHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._parts: list[str] = []
        self.title: str | None = None
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in {"p", "br", "div", "section", "article", "li", "h1", "h2", "h3"}:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False
            title = _normalize_whitespace(" ".join(self._title_parts))
            self.title = title or self.title
        elif tag in {"p", "div", "section", "article", "li", "h1", "h2", "h3"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data)
        if not self._skip_depth and not self._in_title:
            self._parts.append(data)

    def text(self) -> str:
        return _normalize_whitespace(" ".join(self._parts))


def ingest_source_text(
    title: str,
    body: str,
    source_type: str,
    company: str = "deel",
) -> dict[str, Any]:
    normalized_company = _normalize_company(company)
    normalized_title = _require_text(title, "title")
    normalized_body = _normalize_whitespace(_require_text(body, "body"))
    normalized_source_type = _require_text(source_type, "source_type").lower()
    body_bytes = body.encode("utf-8")

    return _save_source_record(
        title=normalized_title,
        text=normalized_body,
        source_type=normalized_source_type,
        company=normalized_company,
        byte_count=len(body_bytes),
    )


def ingest_source_file(path: str | Path, company: str = "deel") -> dict[str, Any]:
    normalized_company = _normalize_company(company)
    source_path = Path(path)
    if not source_path.exists() or not source_path.is_file():
        raise ValueError(f"Source file does not exist: {source_path}")

    suffix = source_path.suffix.lower()
    source_bytes = source_path.read_bytes()
    title = source_path.stem

    if suffix in {".md", ".txt"}:
        text = _normalize_whitespace(source_bytes.decode("utf-8"))
    elif suffix in {".html", ".htm"}:
        parser = _ReadableHTMLParser()
        parser.feed(source_bytes.decode("utf-8"))
        text = parser.text()
        title = parser.title or title
    elif suffix == ".pdf":
        text = _extract_pdf_text(source_path)
    else:
        supported = ", ".join(sorted(SUPPORTED_TEXT_SUFFIXES | {".pdf"}))
        raise ValueError(f"Unsupported source file type '{suffix}'. Supported types: {supported}.")

    return _save_source_record(
        title=title,
        text=text,
        source_type=suffix.removeprefix("."),
        company=normalized_company,
        byte_count=len(source_bytes),
    )


def _save_source_record(
    *,
    title: str,
    text: str,
    source_type: str,
    company: str,
    byte_count: int,
) -> dict[str, Any]:
    normalized_text = _normalize_whitespace(text)
    if not normalized_text:
        raise ValueError("Source text is empty after extraction.")

    content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    filename = f"{_safe_slug(title)}-{content_hash[:10]}.md"
    destination = SOURCES_DIR / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        _format_record(
            title=title,
            source_type=source_type,
            company=company,
            content_hash=content_hash,
            text=normalized_text,
        ),
        encoding="utf-8",
    )

    return {
        "ok": True,
        "path": str(destination),
        "title": title,
        "source_type": source_type,
        "company": company,
        "bytes": byte_count,
        "text_length": len(normalized_text),
        "content_hash": content_hash,
    }


def _format_record(
    *,
    title: str,
    source_type: str,
    company: str,
    content_hash: str,
    text: str,
) -> str:
    return (
        "---\n"
        f"title: {title}\n"
        f"source_type: {source_type}\n"
        f"company: {company}\n"
        f"content_hash: {content_hash}\n"
        "---\n\n"
        f"{text}\n"
    )


def _normalize_company(company: str) -> str:
    normalized = _require_text(company, "company").strip().lower()
    if normalized != "deel":
        raise ValueError("Only Deel source intake is supported.")
    return "deel"


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:72].strip("-") or "source"


def _normalize_whitespace(value: str) -> str:
    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in value.splitlines()]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(line for line in lines if line)).strip()


def _extract_pdf_text(path: Path) -> str:
    if util.find_spec("pypdf") is not None:
        pypdf = import_module("pypdf")
        reader = pypdf.PdfReader(str(path))
        return _normalize_whitespace("\n".join(page.extract_text() or "" for page in reader.pages))

    if util.find_spec("PyPDF2") is not None:
        pypdf2 = import_module("PyPDF2")
        reader = pypdf2.PdfReader(str(path))
        return _normalize_whitespace("\n".join(page.extract_text() or "" for page in reader.pages))

    raise ValueError(
        "PDF source intake requires an installed lightweight PDF parser such as pypdf or PyPDF2."
    )
