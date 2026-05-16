from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import Settings, get_settings
from .retrieval import save_local_chunks, split_markdown


def demo_paths(settings: Settings | None = None) -> list[Path]:
    settings = settings or get_settings()
    return [
        *sorted(settings.sources_dir.glob("*.md")),
        settings.wiki_dir / "deel.md",
    ]


def _normalize_cognee_status(result: dict[str, Any]) -> str:
    status = str(result.get("status", "")).lower()
    if status in {"missing", "missing_dependency"}:
        return "missing"
    if status == "error" or result.get("ok") is False:
        return "error"
    if result.get("cognify_status") == "completed":
        return "indexed"
    if result.get("cognify_status") == "skipped" or status in {"ingested", "added"}:
        return "added_not_cognified"
    return "error"


def _try_cognee_ingest(paths: list[Path], settings: Settings) -> dict[str, Any]:
    try:
        from app.cognee_client import CogneeClient
    except Exception:
        return {"status": "missing", "message": "Cognee package/helpers are not available"}

    client = CogneeClient()
    statuses: list[str] = []
    results: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        result = client.ingest_text(
            title=path.stem,
            content=path.read_text(encoding="utf-8", errors="ignore"),
            metadata={"path": str(path), "company": "deel"},
        )
        results.append(result)
        statuses.append(_normalize_cognee_status(result))

    if not statuses:
        return {"status": "error", "message": "No files were available for Cognee ingestion"}
    if "indexed" in statuses:
        status = "indexed"
    elif "added_not_cognified" in statuses:
        status = "added_not_cognified"
    elif all(item == "missing" for item in statuses):
        status = "missing"
    else:
        status = "error"
    return {"status": status, "files": len(results), "results": results[:3]}


def ingest_demo_data(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    paths = demo_paths(settings)
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing demo files: {missing}")

    chunks: list[dict[str, Any]] = []
    per_file = []
    for path in paths:
        file_chunks = split_markdown(path, company="deel")
        chunks.extend(file_chunks)
        per_file.append({"path": str(path), "chunks": len(file_chunks)})
    save_local_chunks(chunks, settings=settings)
    cognee_result = _try_cognee_ingest(paths, settings)
    return {
        "ok": True,
        "files": per_file,
        "chunks": len(chunks),
        "local_index": str(settings.local_chunk_path),
        "cognee": cognee_result,
    }
