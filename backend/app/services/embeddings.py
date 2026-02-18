from typing import Iterable, List

from openai import OpenAI

from app.config import Settings, get_settings


class EmbeddingService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        self.model_name = "text-embedding-3-small"

    def embed_chunks(self, chunks: Iterable[str]) -> List[List[float]]:
        inputs = list(chunks)
        if not inputs:
            return []
        response = self.client.embeddings.create(model=self.model_name, input=inputs)
        vectors: List[List[float]] = []
        for item in response.data:
            vectors.append(item.embedding)
        return vectors

