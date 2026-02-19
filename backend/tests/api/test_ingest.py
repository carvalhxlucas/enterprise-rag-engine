from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestIngestUpload:
    def test_upload_rejects_missing_filename(self, client):
        response = client.post(
            "/api/v1/ingest/upload",
            headers={"X-User-ID": "user-1"},
            files={"file": ("", BytesIO(b"content"), "application/octet-stream")},
        )
        assert response.status_code in (400, 422)
        detail = response.json().get("detail", "") or ""
        if isinstance(detail, list):
            detail = " ".join(str(d.get("msg", d)) for d in detail)
        assert "filename" in detail.lower() or response.status_code == 422

    def test_upload_accepts_valid_pdf_and_returns_task_id(
        self, client, mock_storage_service, mock_ingest_task
    ):
        with patch("app.api.v1.routers.ingest.validate_mime_type", return_value="application/pdf"):
            response = client.post(
                "/api/v1/ingest/upload",
                headers={"X-User-ID": "user-1"},
                files={"file": ("doc.pdf", BytesIO(b"%PDF-1.4 content"), "application/pdf")},
            )
        assert response.status_code == 202
        data = response.json()
        assert data["task_id"] == "test-task-id-123"
        mock_storage_service.save_file.assert_called_once()
        mock_ingest_task.delay.assert_called_once()

    def test_upload_rejects_unsupported_mime(self, client, mock_storage_service):
        with patch(
            "app.api.v1.routers.ingest.validate_mime_type",
            side_effect=Exception("Unsupported type"),
        ):
            response = client.post(
                "/api/v1/ingest/upload",
                headers={"X-User-ID": "user-1"},
                files={"file": ("file.exe", BytesIO(b"binary"), "application/octet-stream")},
            )
        assert response.status_code in (400, 500)


@pytest.mark.unit
class TestIngestStatus:
    def test_status_pending_returns_pending_response(self, client, mock_celery_async_result):
        mock_result = MagicMock()
        mock_result.state = "PENDING"
        mock_celery_async_result.return_value = mock_result
        response = client.get("/api/v1/ingest/status/task-123")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["progress"] == 0
        assert data["error"] is None

    def test_status_processing_returns_progress(self, client, mock_celery_async_result):
        mock_result = MagicMock()
        mock_result.state = "PROCESSING"
        mock_result.info = {"step": "embedding", "progress": 50}
        mock_celery_async_result.return_value = mock_result
        response = client.get("/api/v1/ingest/status/task-456")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["step"] == "embedding"
        assert data["progress"] == 50

    def test_status_success_returns_completed(self, client, mock_celery_async_result):
        mock_result = MagicMock()
        mock_result.state = "SUCCESS"
        mock_celery_async_result.return_value = mock_result
        response = client.get("/api/v1/ingest/status/task-789")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["progress"] == 100

    def test_status_failure_returns_error_message(self, client, mock_celery_async_result):
        mock_result = MagicMock()
        mock_result.state = "FAILURE"
        mock_result.info = {"step": "chunking", "error": "Parse error"}
        mock_celery_async_result.return_value = mock_result
        response = client.get("/api/v1/ingest/status/task-fail")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error"] == "Parse error"
