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

    try:
        file_content = await file.read()
    except Exception as e:
        logger.exception("Failed to read upload body: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read file content",
        )

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

    try:
        storage_service = StorageService()
        saved_path = storage_service.save_file(file_content, file.filename, user_id)
        task = ingest_document_task.delay(saved_path, user_id, file.filename, mime_type)
    except Exception as e:
        logger.exception("Storage or task enqueue error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload processing failed",
        )

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

    try:
        state = task_result.state
    except Exception:
        return IngestionStatusResponse(status="unknown", step=None, progress=0, error=None)

    if state == "PENDING":
        return IngestionStatusResponse(
            status="pending",
            step=None,
            progress=0,
            error=None,
        )
    
    if state == "PROCESSING":
        meta = task_result.info or {}
        return IngestionStatusResponse(
            status="processing",
            step=meta.get("step"),
            progress=meta.get("progress", 0),
            error=None,
        )

    if state == "SUCCESS":
        result = task_result.result or {}
        return IngestionStatusResponse(
            status="completed",
            step="completed",
            progress=100,
            error=None,
            document_id=result.get("document_id") if isinstance(result, dict) else None,
        )

    if state == "FAILURE":
        info = task_result.info
        if isinstance(info, dict):
            error_msg = info.get("error", str(info))
            step = info.get("step", "error")
        elif isinstance(info, Exception):
            error_msg = str(info)
            step = "error"
        else:
            error_msg = str(info) if info else "Unknown error"
            step = "error"
        return IngestionStatusResponse(
            status="failed",
            step=step,
            progress=0,
            error=error_msg,
        )

    return IngestionStatusResponse(
        status="unknown",
        step=None,
        progress=0,
        error=f"Unknown task state: {state}",
    )
