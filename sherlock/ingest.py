from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from .config import Settings, get_settings
from .retrieval import save_local_chunks, split_markdown


def demo_paths(settings: Settings | None = None) -> list[Path]:
    settings = settings or get_settings()
    return [
        settings.wiki_dir / "deel.md",
        settings.sources_dir / "gong_deel_transcript.md",
        settings.sources_dir / "g2_deel_review.md",
        settings.sources_dir / "deel_product_launch.md",
    ]


def _try_cognee_ingest(paths: list[Path], settings: Settings) -> dict[str, Any]:
    try:
        import cognee
        from cognee import config as cognee_config
    except ImportError:
        return {"status": "missing", "message": "Cognee package is not installed"}

    async def _run() -> dict[str, Any]:
        try:
            cognee_config.set_llm_config(
                {
                    "llm_provider": settings.llm_provider,
                    "llm_model": settings.llm_model,
                    "llm_api_key": settings.llm_api_key,
                }
            )
            cognee_config.set_embedding_config(
                {
                    "embedding_provider": settings.embedding_provider,
                    "embedding_model": settings.embedding_model,
                    "embedding_dimensions": settings.embedding_dimensions,
                    "embedding_api_key": settings.llm_api_key,
                }
            )
            cognee_config.set_vector_db_config(
                {
                    "vector_db_provider": settings.vector_db_provider,
                    "vector_db_url": settings.vector_db_url,
                }
            )
            for path in paths:
                await cognee.add(
                    path.read_text(encoding="utf-8"),
                    dataset_name=settings.cognee_dataset_name,
                )
            if settings.cognee_skip_cognify or settings.mock_embedding or not settings.llm_api_key:
                return {
                    "status": "added",
                    "cognify": "skipped",
                    "reason": "COGNEE_SKIP_COGNIFY, MOCK_EMBEDDING, or missing LLM key",
                }
            await cognee.cognify(datasets=[settings.cognee_dataset_name])
            return {"status": "indexed", "cognify": "completed"}
        except Exception as exc:
            return {"status": "error", "message": str(exc)}

    return asyncio.run(_run())


def ingest_demo_data(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    paths = demo_paths(settings)
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing demo files: {missing}")

    chunks: list[dict[str, Any]] = []
    per_file = []
    for path in paths:
        file_chunks = split_markdown(path, competitor="deel")
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
