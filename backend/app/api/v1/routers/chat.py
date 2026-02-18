from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.core.security import get_current_user_id
from app.models.schemas import ChatRequest
from app.services.chat import ChatOrchestrator


router = APIRouter()


@router.post(
    "/chat/stream",
    status_code=status.HTTP_200_OK,
)
async def chat_stream(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id),
):
    orchestrator = ChatOrchestrator()
    generator = orchestrator.stream_chat(request, user_id)
    return StreamingResponse(generator, media_type="text/event-stream")

