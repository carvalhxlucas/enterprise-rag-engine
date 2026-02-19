import pytest

from app.config import Settings, get_settings


@pytest.mark.unit
class TestSettings:
    def test_default_app_name(self):
        settings = Settings(
            database_url="postgresql+asyncpg://localhost/db",
            qdrant_url="http://localhost:6333",
            redis_url="redis://localhost:6379",
        )
        assert settings.app_name == "Enterprise RAG Engine"

    def test_allowed_origins_from_env_alias(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.com,https://b.com")
        get_settings.cache_clear()
        try:
            settings = get_settings()
            assert len(settings.allowed_origins) == 2
            assert "https://a.com" in str(settings.allowed_origins[0])
            assert "https://b.com" in str(settings.allowed_origins[1])
        finally:
            get_settings.cache_clear()

    def test_allowed_origins_empty_default(self):
        settings = Settings(
            database_url="postgresql+asyncpg://localhost/db",
            qdrant_url="http://localhost:6333",
            redis_url="redis://localhost:6379",
        )
        assert settings.allowed_origins == []

    def test_allowed_hosts_default_wildcard(self):
        settings = Settings(
            database_url="postgresql+asyncpg://localhost/db",
            qdrant_url="http://localhost:6333",
            redis_url="redis://localhost:6379",
        )
        assert settings.allowed_hosts == ["*"]

    def test_allowed_hosts_from_env(self, monkeypatch):
        monkeypatch.setenv("ALLOWED_HOSTS", "host1.com,host2.com")
        get_settings.cache_clear()
        try:
            settings = get_settings()
            assert settings.allowed_hosts == ["host1.com", "host2.com"]
        finally:
            get_settings.cache_clear()

    def test_storage_path_default(self):
        settings = Settings(
            database_url="postgresql+asyncpg://localhost/db",
            qdrant_url="http://localhost:6333",
            redis_url="redis://localhost:6379",
        )
        assert settings.storage_path == "./storage"


@pytest.mark.unit
class TestGetSettings:
    def test_returns_settings_instance(self):
        get_settings.cache_clear()
        try:
            result = get_settings()
            assert isinstance(result, Settings)
        finally:
            get_settings.cache_clear()
