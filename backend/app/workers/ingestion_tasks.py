import asyncio
import logging
from pathlib import Path
from typing import List, Tuple

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Document
from app.db.session import AsyncSessionLocal
from app.services.embeddings import EmbeddingService
from app.utils.chunking import chunk_pages
from app.utils.text_extraction import extract_docx_text, extract_pdf_text, extract_txt_text
from app.workers.celery_app import celery_app


logger = logging.getLogger("enterprise_rag.ingestion")


async def create_document_record(user_id: str, filename: str, mime_type: str, storage_path: str) -> Document:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        document = Document(
            user_id=user_id,
            filename=filename,
            mime_type=mime_type,
            storage_path=storage_path,
        )
        session.add(document)
        await session.commit()
        await session.refresh(document)
        return document


async def update_document_status(document_id, status: str, error_message: str | None = None) -> None:
    async with AsyncSessionLocal() as session:  # type: AsyncSession
        document = await session.get(Document, document_id)
        if document is None:
            return
        document.status = status
        document.error_message = error_message
        await session.commit()


def build_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)


def ensure_qdrant_collection(client: QdrantClient, vector_size: int) -> None:
    collection_name = "documents"
    try:
        client.get_collection(collection_name=collection_name)
        return
    except Exception:
        pass
    client.recreate_collection(
        collection_name=collection_name,
        vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE),
    )


def extract_pages_by_mime(file_path: Path, mime_type: str) -> List[Tuple[int, str]]:
    if mime_type == "application/pdf":
        return extract_pdf_text(file_path)
    if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return extract_docx_text(file_path)
    if mime_type == "text/plain":
        return extract_txt_text(file_path)
    raise ValueError(f"Unsupported MIME type for extraction: {mime_type}")


@celery_app.task(bind=True, name="ingest_document_task")
def ingest_document_task(self, file_path: str, user_id: str, filename: str, mime_type: str) -> dict:
    settings = get_settings()
    storage_path = file_path
    try:
        self.update_state(state="PROCESSING", meta={"step": "extracting_text", "progress": 10})
        logger.info("Starting ingestion for file: %s (user: %s)", file_path, user_id)

        path = Path(file_path)
        pages = extract_pages_by_mime(path, mime_type)

        if not pages:
            raise ValueError("No extractable content found in document")

        self.update_state(state="PROCESSING", meta={"step": "chunking", "progress": 30})
        page_chunks = chunk_pages(pages, chunk_size=1500, chunk_overlap=200)

        texts = [chunk for _, _, chunk in page_chunks]

        self.update_state(state="PROCESSING", meta={"step": "generating_embeddings", "progress": 60})
        embedding_service = EmbeddingService(settings)
        vectors = embedding_service.embed_chunks(texts)

        if not vectors:
            raise ValueError("Failed to generate embeddings")

        vector_size = len(vectors[0])

        client = build_qdrant_client()
        ensure_qdrant_collection(client, vector_size)

        self.update_state(state="PROCESSING", meta={"step": "storing_vectors", "progress": 85})

        document = asyncio.run(create_document_record(user_id, filename, mime_type, storage_path))

        points = []
        for (page_number, chunk_index, _), vector in zip(page_chunks, vectors):
            payload = {
                "user_id": user_id,
                "doc_id": str(document.id),
                "page_number": page_number,
                "access_level": "admin",
                "chunk_index": chunk_index,
                "filename": filename,
            }
            points.append(
                qmodels.PointStruct(
                    id=None,
                    vector=vector,
                    payload=payload,
                )
            )

        client.upsert(collection_name="documents", points=points)

        asyncio.run(update_document_status(document.id, "completed"))

        self.update_state(state="PROCESSING", meta={"step": "finalizing", "progress": 95})

        logger.info("Ingestion completed for file: %s", file_path)
        return {
            "status": "completed",
            "step": "completed",
            "progress": 100,
            "file_path": file_path,
            "document_id": str(document.id),
        }
    except Exception as e:
        logger.exception("Ingestion failed for file: %s", file_path)
        try:
            if "document" in locals():
                asyncio.run(update_document_status(document.id, "failed", str(e)))
        except Exception:
            logger.exception("Failed to update document status after error")
        self.update_state(state="FAILURE", meta={"step": "error", "progress": 0, "error": str(e)})
        raise