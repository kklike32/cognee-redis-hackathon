from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parent.parent


def _load_env() -> None:
    if load_dotenv is not None:
        load_dotenv(ROOT / ".env")
    os.environ.setdefault("ENABLE_BACKEND_ACCESS_CONTROL", "false")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    root_dir: Path = ROOT
    redis_url: str = "redis://localhost:6379/0"
    cognee_dataset_name: str = "sherlock_deel_demo"
    cognee_skip_cognify: bool = True
    mock_embedding: bool = True
    llm_provider: str = "openai"
    llm_model: str = "gpt-5.4-mini"
    llm_api_key: str | None = None
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    vector_db_provider: str = "redis"
    vector_db_url: str = "redis://localhost:6379"
    cache_ttl_seconds: int = 900
    default_company: str = "deel"

    @property
    def data_dir(self) -> Path:
        return self.root_dir / "data"

    @property
    def wiki_dir(self) -> Path:
        return self.data_dir / "wiki"

    @property
    def sources_dir(self) -> Path:
        return self.data_dir / "sources"

    @property
    def pending_path(self) -> Path:
        return self.data_dir / "pending" / "pending_changes.json"

    @property
    def local_chunk_path(self) -> Path:
        return self.root_dir / ".cache" / "sherlock_chunks.json"


def _redis_url_from_env() -> str:
    explicit = os.getenv("REDIS_URL")
    if explicit and explicit.strip():
        return explicit
    host = os.getenv("REDIS_HOST", "localhost")
    port = os.getenv("REDIS_PORT", "6379")
    return f"redis://{host}:{port}/0"


def get_settings() -> Settings:
    _load_env()
    return Settings(
        redis_url=_redis_url_from_env(),
        cognee_dataset_name=os.getenv("COGNEE_DATASET_NAME", "sherlock_deel_demo"),
        cognee_skip_cognify=_env_bool("COGNEE_SKIP_COGNIFY", True),
        mock_embedding=_env_bool("MOCK_EMBEDDING", True),
        llm_provider=os.getenv("LLM_PROVIDER", "openai"),
        llm_model=os.getenv("LLM_MODEL", "gpt-5.4-mini"),
        llm_api_key=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or None,
        embedding_provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
        embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        embedding_dimensions=_env_int("EMBEDDING_DIMENSIONS", 1536),
        vector_db_provider=os.getenv("VECTOR_DB_PROVIDER", "redis"),
        vector_db_url=os.getenv("VECTOR_DB_URL", "redis://localhost:6379"),
        cache_ttl_seconds=_env_int("SHERLOCK_CACHE_TTL_SECONDS", 900),
        default_company=os.getenv("SHERLOCK_COMPANY", "deel").lower(),
    )
