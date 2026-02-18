from fastapi import APIRouter, UploadFile, status


router = APIRouter()


@router.post(
    "/ingest",
    status_code=status.HTTP_202_ACCEPTED,
)
async def enqueue_ingestion(file: UploadFile):
    return {"status": "accepted"}

