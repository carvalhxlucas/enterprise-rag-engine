import logging
from typing import Annotated

from celery.result import AsyncResult
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.core.security import get_current_user_id
from app.models.schemas import IngestionStatusResponse, UploadResponse
from app.services.storage import StorageService
from app.utils.mime_validator import validate_mime_type
from app.workers.celery_app import celery_app
from app.workers.ingestion_tasks import ingest_document_task

logger = logging.getLogger("enterprise_rag.ingestion")

router = APIRouter()


@router.post(
    "/ingest/upload",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=UploadResponse,
)
async def upload_document(
    file: UploadFile,
    user_id: Annotated[str, Depends(get_current_user_id)],
) -> UploadResponse:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required",
        )

    file_content = await file.read()

    try:
        mime_type = validate_mime_type(file_content, file.filename)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("MIME validation error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"MIME validation failed: {str(e)}",
        )

    storage_service = StorageService()
    saved_path = storage_service.save_file(file_content, file.filename, user_id)

    task = ingest_document_task.delay(saved_path, user_id, file.filename, mime_type)
    
    logger.info(
        "File uploaded: %s (user: %s, task_id: %s)",
        file.filename,
        user_id,
        task.id,
    )

    return UploadResponse(task_id=task.id)


@router.get(
    "/ingest/status/{task_id}",
    status_code=status.HTTP_200_OK,
    response_model=IngestionStatusResponse,
)
async def get_ingestion_status(task_id: str) -> IngestionStatusResponse:
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.state == "PENDING":
        return IngestionStatusResponse(
            status="pending",
            step=None,
            progress=0,
            error=None,
        )
    
    if task_result.state == "PROCESSING":
        meta = task_result.info or {}
        return IngestionStatusResponse(
            status="processing",
            step=meta.get("step"),
            progress=meta.get("progress", 0),
            error=None,
        )
    
    if task_result.state == "SUCCESS":
        return IngestionStatusResponse(
            status="completed",
            step="completed",
            progress=100,
            error=None,
        )
    
    if task_result.state == "FAILURE":
        meta = task_result.info or {}
        error_msg = str(task_result.info) if isinstance(task_result.info, (str, dict)) else "Unknown error"
        if isinstance(meta, dict) and "error" in meta:
            error_msg = meta["error"]
        return IngestionStatusResponse(
            status="failed",
            step=meta.get("step", "error") if isinstance(meta, dict) else "error",
            progress=0,
            error=error_msg,
        )
    
    return IngestionStatusResponse(
        status="unknown",
        step=None,
        progress=0,
        error=f"Unknown task state: {task_result.state}",
    )
