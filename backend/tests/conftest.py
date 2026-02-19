import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/test_db")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.main import app as fastapi_app


@pytest.fixture
def app():
    return fastapi_app


@pytest.fixture
def client(app):
    with (
        patch("app.main.init_db", new_callable=AsyncMock) as _,
        patch("app.main.get_qdrant_client") as mock_qdrant,
    ):
        mock_qdrant.return_value = MagicMock()
        with TestClient(app) as test_client:
            yield test_client


@pytest.fixture
def mock_storage_service():
    with patch("app.api.v1.routers.ingest.StorageService") as mock:
        instance = MagicMock()
        instance.save_file.return_value = "/tmp/test_user/uuid_doc.pdf"
        mock.return_value = instance
        yield instance


@pytest.fixture
def mock_ingest_task():
    with patch("app.api.v1.routers.ingest.ingest_document_task") as mock:
        mock_result = MagicMock()
        mock_result.id = "test-task-id-123"
        mock.delay.return_value = mock_result
        yield mock


@pytest.fixture
def mock_celery_async_result():
    with patch("app.api.v1.routers.ingest.AsyncResult") as mock:
        yield mock
