from app.config import Settings, get_settings


def test_settings_redis_url_takes_precedence(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "rediss://example:6379/0")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.redis_dsn == "rediss://example:6379/0"


def test_settings_builds_dsn_from_fields(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("REDIS_HOST", "cache.example.com")
    monkeypatch.setenv("REDIS_PORT", "6380")
    monkeypatch.setenv("REDIS_USERNAME", "default")
    monkeypatch.setenv("REDIS_PASSWORD", "secret")
    monkeypatch.setenv("REDIS_SSL", "true")
    get_settings.cache_clear()

    settings = Settings()

    assert settings.redis_dsn == "rediss://default:secret@cache.example.com:6380/0"


def test_local_defaults_are_set():
    settings = Settings(_env_file=None)

    assert settings.redis_host == "localhost"
    assert settings.redis_ssl is False
    assert settings.cognee_dataset_name == "default_dataset"
    assert settings.llm_provider == "openai"
    assert settings.embedding_provider == "openai"
    assert settings.embedding_dimensions == 1536
    assert settings.vector_db_url == "redis://localhost:6379"
    assert settings.enable_backend_access_control is False
    assert settings.mock_embedding is False
    assert settings.cognee_skip_cognify is False
