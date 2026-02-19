import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.services.storage import StorageService


@pytest.mark.unit
class TestStorageService:
    def test_save_file_creates_user_dir_and_file(self, tmp_path):
        with patch("app.services.storage.get_settings") as mock_get:
            mock_settings = MagicMock()
            mock_settings.storage_path = str(tmp_path)
            mock_get.return_value = mock_settings
            service = StorageService(settings=mock_settings)
            content = b"file content"
            path = service.save_file(content, "test.txt", "user-1")
            assert path is not None
            assert Path(path).exists()
            assert Path(path).read_bytes() == content
            assert "user-1" in path
            assert "test.txt" in path

    def test_save_file_returns_absolute_path_string(self, tmp_path):
        with patch("app.services.storage.get_settings") as mock_get:
            mock_settings = MagicMock()
            mock_settings.storage_path = str(tmp_path)
            mock_get.return_value = mock_settings
            service = StorageService(settings=mock_settings)
            path = service.save_file(b"x", "a.txt", "u")
            assert isinstance(path, str)
            assert Path(path).is_absolute() or path.startswith(".")

    def test_get_file_path_returns_none_when_no_match(self, tmp_path):
        with patch("app.services.storage.get_settings") as mock_get:
            mock_settings = MagicMock()
            mock_settings.storage_path = str(tmp_path)
            mock_get.return_value = mock_settings
            service = StorageService(settings=mock_settings)
            result = service.get_file_path(str(uuid.uuid4()), "user-1")
            assert result is None

    def test_get_file_path_returns_path_when_file_exists(self, tmp_path):
        with patch("app.services.storage.get_settings") as mock_get:
            mock_settings = MagicMock()
            mock_settings.storage_path = str(tmp_path)
            mock_get.return_value = mock_settings
            service = StorageService(settings=mock_settings)
            saved = service.save_file(b"content", "doc.pdf", "user-1")
            file_id = Path(saved).stem.split("_", 1)[0]
            result = service.get_file_path(file_id, "user-1")
            assert result is not None
            assert result.read_bytes() == b"content"

    def test_read_file_returns_file_bytes(self, tmp_path):
        with patch("app.services.storage.get_settings") as mock_get:
            mock_settings = MagicMock()
            mock_settings.storage_path = str(tmp_path)
            mock_get.return_value = mock_settings
            service = StorageService(settings=mock_settings)
            path = service.save_file(b"read me", "f.txt", "u")
            assert service.read_file(path) == b"read me"
