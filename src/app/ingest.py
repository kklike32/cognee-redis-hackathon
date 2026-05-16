from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .cognee_client import CogneeClient
from .config import get_settings
from .local_store import save_local_chunks
from .redis_client import embed_text, upsert_knowledge_chunks

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "document"


def _split_markdown_into_chunks(content: str, source_path: str) -> list[dict[str, Any]]:
    heading_stack: list[tuple[int, str]] = []
    buffered_lines: list[str] = []
    chunks: list[dict[str, Any]] = []

    def current_title() -> str:
        if heading_stack:
            return " > ".join(title for _, title in heading_stack)
        return Path(source_path).stem

    def flush_buffer() -> None:
        nonlocal buffered_lines
        text = "\n".join(buffered_lines).strip()
        buffered_lines = []
        if not text:
            return

        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        for paragraph in paragraphs:
            chunks.append(
                {
                    "title": current_title(),
                    "text": paragraph,
                    "source": source_path,
                    "heading_path": current_title(),
                }
            )

    for line in content.splitlines():
        match = HEADING_RE.match(line)
        if match:
            flush_buffer()
            level = len(match.group(1))
            heading = match.group(2).strip()
            heading_stack[:] = [(h_level, h_title) for h_level, h_title in heading_stack if h_level < level]
            heading_stack.append((level, heading))
            continue
        buffered_lines.append(line)

    flush_buffer()
    return chunks


def ingest_markdown_file(path: str) -> dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Markdown file not found: {file_path}")

    raw_content = file_path.read_text(encoding="utf-8")
    parsed_chunks = _split_markdown_into_chunks(raw_content, str(file_path))

    timestamp = datetime.now(timezone.utc).isoformat()
    document_id = _slugify(file_path.stem)
    records: list[dict[str, Any]] = []

    for index, chunk in enumerate(parsed_chunks):
        chunk_text = chunk["text"]
        chunk_id_source = f"{file_path}:{index}:{chunk_text}"
        chunk_id = str(uuid.uuid5(uuid.NAMESPACE_URL, hashlib.sha1(chunk_id_source.encode("utf-8")).hexdigest()))
        records.append(
            {
                "id": chunk_id,
                "title": chunk["title"],
                "text": chunk_text,
                "source": str(file_path),
                "agent_type": "ingest",
                "created_at": timestamp,
                "metadata": {
                    "document_id": document_id,
                    "heading_path": chunk["heading_path"],
                    "chunk_index": index,
                },
                "embedding": embed_text(chunk_text),
            }
        )

    settings = get_settings()
    cognee_result = CogneeClient(settings).ingest_text(
        title=file_path.stem,
        content=raw_content,
        metadata={
            "path": str(file_path),
            "chunks": len(records),
            "document_id": document_id,
        },
    )

    redis_result = upsert_knowledge_chunks(records, settings=settings) if records else {"ok": True, "stored": 0}
    save_local_chunks(records)

    return {
        "ok": True,
        "document": file_path.name,
        "document_id": document_id,
        "chunks": len(records),
        "cognee": cognee_result,
        "redis": redis_result,
        "sample_chunks": records[:3],
    }

