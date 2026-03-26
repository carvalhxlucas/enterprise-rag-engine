import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from qdrant_client.http import models as qmodels
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user_id
from app.db.models import Document
from app.db.session import get_db_session
from app.dependencies import get_qdrant_client

logger = logging.getLogger("enterprise_rag.documents")

router = APIRouter()


@router.get("/documents", status_code=status.HTTP_200_OK)
async def list_documents(
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
):
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return {
        "documents": [
            {
                "id": str(d.id),
                "filename": d.filename,
                "status": d.status,
                "created_at": d.created_at.isoformat(),
            }
            for d in docs
        ]
    }


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> None:
    document = await db.get(Document, document_id)
    if document is None or document.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        qdrant = get_qdrant_client()
        qdrant.delete(
            collection_name="documents",
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(key="doc_id", match=qmodels.MatchValue(value=document_id)),
                        qmodels.FieldCondition(key="user_id", match=qmodels.MatchValue(value=user_id)),
                    ]
                )
            ),
        )
    except Exception:
        logger.exception("Failed to delete vectors from Qdrant for document %s", document_id)

    try:
        file_path = Path(document.storage_path)
        if file_path.exists():
            file_path.unlink()
    except Exception:
        logger.exception("Failed to delete file for document %s", document_id)

    await db.delete(document)
    await db.commit()
