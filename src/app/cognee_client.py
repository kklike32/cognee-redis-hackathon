from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from .config import Settings, get_settings
from .redis_client import ping_redis

try:  # Optional at import time so the repo still imports without Cognee installed.
    import cognee
    from cognee import SearchType
    from cognee import config as cognee_config
except ImportError:  # pragma: no cover - dependency guard
    cognee = None  # type: ignore[assignment]
    SearchType = None  # type: ignore[assignment]
    cognee_config = None  # type: ignore[assignment]

try:  # Optional local adapter for the Redis vector store.
    import cognee_community_vector_adapter_redis.register  # noqa: F401
except ImportError:  # pragma: no cover - dependency guard
    pass

try:  # Optional helper to attach metadata to the added payload.
    from cognee.tasks.ingestion.data_item import DataItem
except ImportError:  # pragma: no cover - dependency guard
    DataItem = None  # type: ignore[assignment]


def _run(coro):
    return asyncio.run(coro)


class CogneeClient:
    """Local-first Cognee wrapper.

    This client is intentionally small and keeps the Cognee integration isolated
    so the rest of the app can stay stable while the local stack is configured.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._configured = False

    @property
    def is_configured(self) -> bool:
        return self.sdk_available and self.settings.has_cognee_config

    @property
    def sdk_available(self) -> bool:
        return cognee is not None and cognee_config is not None

    def _configure_local_stack(self) -> None:
        if not self.sdk_available or self._configured:
            return

        llm_config = self._clean_config(
            {
                "llm_provider": self.settings.llm_provider,
                "llm_model": self.settings.llm_model,
                "llm_endpoint": self.settings.llm_endpoint,
                "llm_api_key": self.settings.effective_llm_api_key,
            }
        )
        embedding_config = self._clean_config(
            {
                "embedding_provider": self.settings.embedding_provider,
                "embedding_model": self.settings.embedding_model,
                "embedding_dimensions": self.settings.embedding_dimensions,
                "embedding_endpoint": self.settings.embedding_endpoint,
                "embedding_api_key": self.settings.effective_embedding_api_key,
            }
        )
        vector_config = self._clean_config(
            {
                "vector_db_provider": self.settings.vector_db_provider,
                "vector_db_url": self.settings.vector_db_url,
                "vector_db_key": self.settings.vector_db_key,
            }
        )

        cognee_config.set_llm_config(  # type: ignore[union-attr]
            llm_config
        )
        cognee_config.set_embedding_config(  # type: ignore[union-attr]
            embedding_config
        )
        cognee_config.set_vector_db_config(  # type: ignore[union-attr]
            vector_config
        )
        self._configured = True

    async def ingest_text_async(
        self,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "title": title,
            "content": content,
            "metadata": metadata or {},
        }

        if not self.sdk_available:
            return {
                "ok": False,
                "status": "missing_dependency",
                "message": (
                    "Install `cognee` and `cognee-community-vector-adapter-redis` "
                    "to enable local Cognee ingestion."
                ),
                "payload": payload,
            }

        self._configure_local_stack()

        try:
            data_payload: Any = content
            if DataItem is not None and metadata:
                data_payload = DataItem(
                    data=content,
                    label=title,
                    external_metadata=metadata,
                )

            await cognee.add(  # type: ignore[attr-defined]
                data_payload,
                dataset_name=self.settings.cognee_dataset_name,
            )
            skip_cognify = self.settings.cognee_skip_cognify or self.settings.mock_embedding
            cognify_status = "skipped" if skip_cognify else "completed"
            if not skip_cognify:
                await cognee.cognify(  # type: ignore[attr-defined]
                    datasets=[self.settings.cognee_dataset_name]
                )
            return {
                "ok": True,
                "status": "ingested",
                "title": title,
                "metadata": metadata or {},
                "dataset": self.settings.cognee_dataset_name,
                "transport": "sdk-local",
                "cognify_status": cognify_status,
            }
        except Exception as exc:
            return {
                "ok": False,
                "status": "error",
                "title": title,
                "metadata": metadata or {},
                "message": f"Local Cognee ingest failed: {exc}",
                "payload": payload,
            }

    async def ingest_file_async(self, path: str) -> dict[str, Any]:
        file_path = Path(path)
        content = file_path.read_text(encoding="utf-8")
        return await self.ingest_text_async(
            title=file_path.stem,
            content=content,
            metadata={"path": str(file_path)},
        )

    async def search_async(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        if not self.sdk_available:
            return []

        self._configure_local_stack()

        try:
            search_kwargs: dict[str, Any] = {
                "query_text": query,
                "datasets": [self.settings.cognee_dataset_name],
                "top_k": top_k,
            }
            if SearchType is not None:
                search_kwargs["query_type"] = SearchType.CHUNKS

            results = await cognee.search(  # type: ignore[attr-defined]
                **search_kwargs,
            )

            normalized: list[dict[str, Any]] = []
            for item in results or []:
                normalized.append(self._normalize_result(item))
                if len(normalized) >= top_k:
                    break
            return normalized
        except Exception:
            return []

    def ingest_text(
        self,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return _run(self.ingest_text_async(title=title, content=content, metadata=metadata))

    def ingest_file(self, path: str) -> dict[str, Any]:
        return _run(self.ingest_file_async(path))

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        return _run(self.search_async(query, top_k=top_k))

    def health_check(self) -> dict[str, Any]:
        redis_status = ping_redis(settings=self.settings)
        if not redis_status.get("ok"):
            return {
                "ok": False,
                "status": "error",
                "message": "Cognee depends on a reachable Redis vector store.",
                "redis": redis_status,
            }

        if not self.sdk_available:
            return {
                "ok": False,
                "status": "missing_dependency",
                "message": (
                    "Install `cognee` and `cognee-community-vector-adapter-redis` "
                    "to enable the local Cognee stack."
                ),
                "redis": redis_status,
            }

        try:
            self._configure_local_stack()
            return {
                "ok": True,
                "status": "ready",
                "message": "Local Cognee SDK and Redis vector adapter are configured.",
                "config": {
                    "dataset_name": self.settings.cognee_dataset_name,
                    "llm_provider": self.settings.llm_provider,
                    "embedding_provider": self.settings.embedding_provider,
                    "embedding_dimensions": self.settings.embedding_dimensions,
                    "vector_db_provider": self.settings.vector_db_provider,
                    "vector_db_url": self.settings.vector_db_url,
                },
                "redis": redis_status,
            }
        except Exception as exc:  # pragma: no cover - surfaced in CLI output.
            return {
                "ok": False,
                "status": "error",
                "message": f"Local Cognee configuration failed: {exc}",
                "redis": redis_status,
            }

    @staticmethod
    def _normalize_result(item: Any) -> dict[str, Any]:
        if isinstance(item, dict):
            return item
        if hasattr(item, "model_dump"):
            return item.model_dump()

        normalized: dict[str, Any] = {}
        for key in ("text", "title", "source", "score", "dataset_name", "dataset_id"):
            value = getattr(item, key, None)
            if value is not None:
                normalized[key] = value
        if not normalized:
            normalized["text"] = str(item)
        return normalized

    @staticmethod
    def _clean_config(values: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in values.items() if value is not None}
