from fastapi import APIRouter, status


router = APIRouter()


@router.post(
    "/chat",
    status_code=status.HTTP_200_OK,
)
async def chat():
    return {"message": "not_implemented"}

