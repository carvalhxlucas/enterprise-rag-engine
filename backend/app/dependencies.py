from functools import lru_cache

from qdrant_client import QdrantClient

from app.config import Settings, get_settings


@lru_cache
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def get_app_settings() -> Settings:
    return get_settings()

