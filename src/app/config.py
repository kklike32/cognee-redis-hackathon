from __future__ import annotations

import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

# Cognee reads this directly from os.environ during startup checks.
# Default to the local-demo setting unless the user explicitly overrides it.
os.environ.setdefault("ENABLE_BACKEND_ACCESS_CONTROL", "false")


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int | None = Field(default=6379, alias="REDIS_PORT")
    redis_username: str | None = Field(default=None, alias="REDIS_USERNAME")
    redis_password: str | None = Field(default=None, alias="REDIS_PASSWORD")
    redis_ssl: bool = Field(default=False, alias="REDIS_SSL")
    redis_account_key: str | None = Field(default=None, alias="REDIS_ACCOUNT_KEY")
    redis_api_key: str | None = Field(default=None, alias="REDIS_API_KEY")

    cognee_dataset_name: str = Field(default="default_dataset", alias="COGNEE_DATASET_NAME")
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-5.4-mini", alias="LLM_MODEL")
    llm_endpoint: str | None = Field(default=None, alias="LLM_ENDPOINT")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    embedding_provider: str = Field(default="openai", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS")
    embedding_endpoint: str | None = Field(default=None, alias="EMBEDDING_ENDPOINT")
    embedding_api_key: str | None = Field(default=None, alias="EMBEDDING_API_KEY")
    vector_db_provider: str = Field(default="redis", alias="VECTOR_DB_PROVIDER")
    vector_db_url: str = Field(default="redis://localhost:6379", alias="VECTOR_DB_URL")
    vector_db_key: str | None = Field(default=None, alias="VECTOR_DB_KEY")
    caching: bool = Field(default=False, alias="CACHING")
    cache_backend: str = Field(default="fs", alias="CACHE_BACKEND")
    enable_backend_access_control: bool = Field(
        default=False, alias="ENABLE_BACKEND_ACCESS_CONTROL"
    )
    mock_embedding: bool = Field(default=False, alias="MOCK_EMBEDDING")
    cognee_skip_cognify: bool = Field(default=False, alias="COGNEE_SKIP_COGNIFY")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")

    app_env: str = Field(default="development", alias="APP_ENV")

    @property
    def redis_dsn(self) -> str:
        if self.redis_url:
            return self.redis_url

        host = self.redis_host or "localhost"
        port = self.redis_port or 6379
        scheme = "rediss" if self.redis_ssl else "redis"

        auth = ""
        if self.redis_username and self.redis_password:
            auth = f"{self.redis_username}:{self.redis_password}@"
        elif self.redis_username:
            auth = f"{self.redis_username}@"
        elif self.redis_password:
            auth = f":{self.redis_password}@"

        return f"{scheme}://{auth}{host}:{port}/0"

    @property
    def has_redis_config(self) -> bool:
        return True

    @property
    def has_redis_management_config(self) -> bool:
        return bool(self.redis_account_key and self.redis_api_key)

    @property
    def has_cognee_config(self) -> bool:
        return bool(self.vector_db_provider and self.vector_db_url and self.llm_provider and self.embedding_provider)

    @property
    def effective_llm_api_key(self) -> str | None:
        return self.llm_api_key or self.openai_api_key

    @property
    def effective_embedding_api_key(self) -> str | None:
        return self.embedding_api_key or self.effective_llm_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
