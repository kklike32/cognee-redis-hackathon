from sherlock.config import Settings, get_settings


def test_settings_redis_url_takes_precedence(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "rediss://example:6379/0")
    monkeypatch.setenv("REDIS_HOST", "localhost")

    settings = get_settings()

    assert settings.redis_url == "rediss://example:6379/0"


def test_settings_builds_url_from_fields(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("REDIS_HOST", "cache.example.com")
    monkeypatch.setenv("REDIS_PORT", "6380")

    settings = get_settings()

    assert settings.redis_url == "redis://cache.example.com:6380/0"


def test_local_defaults_are_set():
    settings = Settings()

    assert settings.redis_url == "redis://localhost:6379/0"
    assert settings.cognee_dataset_name == "sherlock_deel_demo"
    assert settings.llm_provider == "openai"
    assert settings.embedding_provider == "openai"
    assert settings.embedding_dimensions == 1536
    assert settings.vector_db_url == "redis://localhost:6379"
    assert settings.mock_embedding is True
    assert settings.cognee_skip_cognify is True
