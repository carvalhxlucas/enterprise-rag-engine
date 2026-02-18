import json
from typing import Iterator

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import Settings, get_settings
from app.dependencies import get_qdrant_client
from app.models.schemas import ChatConfig, ChatRequest
from app.services.embeddings import EmbeddingService


class ChatOrchestrator:
    def __init__(
        self,
        settings: Settings | None = None,
        qdrant_client: QdrantClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.qdrant_client = qdrant_client or get_qdrant_client()
        self.embedding_service = EmbeddingService(self.settings)
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        self.model_name = "gpt-4o-mini"

    def build_system_prompt(self, config: ChatConfig) -> str:
        if config.persona == "sarcastic":
            return (
                "You are a highly knowledgeable but sarcastic assistant. "
                "You answer technical questions accurately, but with dry humor and sharp wit. "
                "Always prioritize correctness over jokes."
            )
        return (
            "You are an extremely technical assistant that explains concepts with precision. "
            "Use rigorous terminology, reference algorithms and data structures when relevant, "
            "and keep answers concise but deeply informative."
        )

    def retrieve_context(self, user_id: str, query: str, config: ChatConfig) -> str:
        if not self.qdrant_client or not self.settings.use_local_embeddings:
            return ""

        vectors = self.embedding_service.embed_chunks([query])
        if not vectors:
            return ""

        vector = vectors[0]

        query_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="user_id",
                    match=qmodels.MatchValue(value=user_id),
                ),
            ]
        )

        search_kwargs = {
            "collection_name": "documents",
            "query_vector": vector,
            "limit": 5,
            "query_filter": query_filter,
        }

        hits = self.qdrant_client.search(**search_kwargs)

        snippets: list[str] = []
        for hit in hits:
            payload = hit.payload or {}
            filename = payload.get("filename")
            page_number = payload.get("page_number")
            chunk_index = payload.get("chunk_index")
            snippets.append(
                f"File: {filename}, page: {page_number}, chunk: {chunk_index}"
            )

        if not snippets:
            return ""

        return "\n".join(snippets)

    def stream_chat(self, request: ChatRequest, user_id: str) -> Iterator[str]:
        system_prompt = self.build_system_prompt(request.config)
        context = self.retrieve_context(user_id, request.message, request.config)

        messages: list[dict[str, str]] = []
        messages.append({"role": "system", "content": system_prompt})

        if context:
            messages.append(
                {
                    "role": "system",
                    "content": f"Use the following context from the user's documents when answering:\n{context}",
                }
            )

        for message in request.history:
            messages.append({"role": message.role, "content": message.content})

        messages.append({"role": "user", "content": request.message})

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=request.config.temperature,
            stream=True,
        )

        for chunk in response:
            choice = chunk.choices[0]
            if not choice.delta or not choice.delta.content:
                continue
            data = {"content": choice.delta.content}
            yield f"data: {json.dumps(data)}\n\n"

        yield "event: end\ndata: {}\n\n"

