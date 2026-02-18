from typing import List, Literal

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    task_id: str = Field(..., description="Celery task ID for tracking ingestion progress")
    message: str = Field(default="File uploaded and ingestion queued", description="Status message")


class IngestionStatusResponse(BaseModel):
    status: str = Field(..., description="Task status: pending, processing, completed, failed")
    step: str | None = Field(None, description="Current processing step")
    progress: int = Field(0, ge=0, le=100, description="Progress percentage (0-100)")
    error: str | None = Field(None, description="Error message if status is failed")


ChatMessageRole = Literal["user", "assistant", "system"]


class ChatMessage(BaseModel):
    role: ChatMessageRole = Field(..., description="Role of the message author")
    content: str = Field(..., description="Message content")


class ChatConfig(BaseModel):
    persona: Literal["sarcastic", "technical"] = Field(
        "technical",
        description="Persona that controls tone and style of the assistant",
    )
    temperature: float = Field(
        0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for the language model",
    )
    use_hybrid_search: bool = Field(
        True,
        description="Whether to use hybrid search (dense + keyword) when retrieving context",
    )


class ChatRequest(BaseModel):
    message: str = Field(..., description="User input message for the assistant")
    history: List[ChatMessage] = Field(
        default_factory=list,
        description="Full chat history including previous user and assistant messages",
    )
    config: ChatConfig = Field(
        default_factory=ChatConfig,
        description="Dynamic configuration for this chat request",
    )
