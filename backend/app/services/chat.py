import json
import time
from typing import Iterator

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config import Settings, get_settings
from app.dependencies import get_qdrant_client
from app.models.schemas import ChatConfig, ChatRequest
from app.services.embeddings import EmbeddingService

# GPT-4o-mini pricing (USD per token)
_PRICE_INPUT = 0.150 / 1_000_000
_PRICE_OUTPUT = 0.600 / 1_000_000


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

    def retrieve_sources(self, user_id: str, query: str) -> list[dict]:
        """Search Qdrant and return a structured list of source chunks."""
        if not self.qdrant_client:
            return []

        vectors = self.embedding_service.embed_chunks([query])
        if not vectors:
            return []

        try:
            hits = self.qdrant_client.search(
                collection_name="documents",
                query_vector=vectors[0],
                limit=5,
                query_filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="user_id",
                            match=qmodels.MatchValue(value=user_id),
                        )
                    ]
                ),
            )
        except Exception:
            return []

        sources: list[dict] = []
        for i, hit in enumerate(hits):
            payload = hit.payload or {}
            text = payload.get("text", "")
            if not text:
                continue
            sources.append(
                {
                    "id": str(i + 1),
                    "filename": payload.get("filename", "unknown"),
                    "page_number": payload.get("page_number"),
                    "chunk_index": payload.get("chunk_index"),
                    "text": text,
                }
            )
        return sources

    def retrieve_context(self, user_id: str, query: str, config: ChatConfig) -> str:
        sources = self.retrieve_sources(user_id, query)
        if not sources:
            return ""
        return "\n\n---\n\n".join(
            f"[Source: {s['filename']}, page {s['page_number']}]\n{s['text']}"
            for s in sources
        )

    def retrieve_context_list(
        self, user_id: str, query: str, config: ChatConfig
    ) -> list[str]:
        return [s["text"] for s in self.retrieve_sources(user_id, query)]

    def get_answer_for_eval(
        self,
        user_id: str,
        question: str,
        config: ChatConfig | None = None,
        contexts_override: list[str] | None = None,
    ) -> tuple[str, list[str]]:
        config = config or ChatConfig(temperature=0.0)
        contexts = (
            contexts_override
            if contexts_override is not None
            else self.retrieve_context_list(user_id, question, config)
        )
        system_prompt = self.build_system_prompt(config)
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]
        if contexts:
            messages.insert(
                1,
                {
                    "role": "system",
                    "content": f"Use the following context from the user's documents when answering:\n"
                    + "\n".join(contexts),
                },
            )
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=config.temperature,
            stream=False,
        )
        return (response.choices[0].message.content or "").strip(), contexts

    def stream_chat(self, request: ChatRequest, user_id: str) -> Iterator[str]:
        sources = self.retrieve_sources(user_id, request.message)

        messages: list[dict[str, str]] = [
            {"role": "system", "content": self.build_system_prompt(request.config)}
        ]

        if sources:
            context_block = "\n\n---\n\n".join(
                f"[{s['id']}] [Source: {s['filename']}, page {s['page_number']}]\n{s['text']}"
                for s in sources
            )
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "Use the following context to answer the user's question. "
                        "When referencing specific information, cite the source number "
                        "in square brackets, e.g. [1].\n\n" + context_block
                    ),
                }
            )

        for msg in request.history:
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": request.message})

        start = time.time()

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=request.config.temperature,
            stream=True,
            stream_options={"include_usage": True},
        )

        prompt_tokens = 0
        completion_tokens = 0

        for chunk in response:
            if not chunk.choices:
                if chunk.usage:
                    prompt_tokens = chunk.usage.prompt_tokens
                    completion_tokens = chunk.usage.completion_tokens
                continue
            choice = chunk.choices[0]
            if not choice.delta or not choice.delta.content:
                continue
            yield f"data: {json.dumps({'content': choice.delta.content})}\n\n"

        if sources:
            yield f"event: citations\ndata: {json.dumps(sources)}\n\n"

        latency_ms = round((time.time() - start) * 1000)
        cost_usd = round(prompt_tokens * _PRICE_INPUT + completion_tokens * _PRICE_OUTPUT, 6)
        yield f"event: metrics\ndata: {json.dumps({'latency_ms': latency_ms, 'cost_usd': cost_usd})}\n\n"

        yield "event: end\ndata: {}\n\n"
