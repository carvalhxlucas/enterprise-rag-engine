from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Enterprise RAG Engine"
    app_env: str = "local"
    debug: bool = True

    database_url: str

    qdrant_url: str
    qdrant_api_key: str | None = None

    redis_url: str

    openai_api_key: str | None = None
    ollama_base_url: str | None = None
    use_local_llm: bool = False
    use_local_embeddings: bool = False

    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: AnyHttpUrl | None = None

    allowed_origins: List[AnyHttpUrl] = []
    allowed_hosts: List[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]

