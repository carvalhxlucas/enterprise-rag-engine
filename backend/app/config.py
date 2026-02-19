from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, Field, computed_field
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

    allowed_origins_raw: str = Field(default="", validation_alias="ALLOWED_ORIGINS")
    allowed_hosts_raw: str = Field(default="*", validation_alias="ALLOWED_HOSTS")

    storage_path: str = "./storage"

    @computed_field
    @property
    def allowed_origins(self) -> List[AnyHttpUrl]:
        return [AnyHttpUrl(u.strip()) for u in self.allowed_origins_raw.split(",") if u.strip()]

    @computed_field
    @property
    def allowed_hosts(self) -> List[str]:
        parts = [h.strip() for h in self.allowed_hosts_raw.split(",") if h.strip()]
        return parts if parts else ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]

