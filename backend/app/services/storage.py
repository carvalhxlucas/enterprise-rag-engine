import os
import uuid
from pathlib import Path
from typing import BinaryIO

from app.config import Settings, get_settings


class StorageService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.storage_path = Path(self.settings.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_content: bytes, filename: str, user_id: str) -> str:
        file_id = str(uuid.uuid4())
        user_dir = self.storage_path / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = user_dir / f"{file_id}_{filename}"
        file_path.write_bytes(file_content)
        
        return str(file_path)

    def get_file_path(self, file_id: str, user_id: str) -> Path | None:
        user_dir = self.storage_path / user_id
        for file_path in user_dir.glob(f"{file_id}_*"):
            return file_path
        return None

    def read_file(self, file_path: str) -> bytes:
        return Path(file_path).read_bytes()
