from typing import Optional

from langfuse import Langfuse

from app.config import get_settings


settings = get_settings()


def create_langfuse_client() -> Optional[Langfuse]:
    if not settings.langfuse_public_key or not settings.langfuse_secret_key or not settings.langfuse_host:
        return None
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=str(settings.langfuse_host),
    )


langfuse_client = create_langfuse_client()

