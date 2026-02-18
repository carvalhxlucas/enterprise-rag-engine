from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    task_id: str = Field(..., description="Celery task ID for tracking ingestion progress")
    message: str = Field(default="File uploaded and ingestion queued", description="Status message")


class IngestionStatusResponse(BaseModel):
    status: str = Field(..., description="Task status: pending, processing, completed, failed")
    step: str | None = Field(None, description="Current processing step")
    progress: int = Field(0, ge=0, le=100, description="Progress percentage (0-100)")
    error: str | None = Field(None, description="Error message if status is failed")
