from fastapi import APIRouter, status


router = APIRouter()


@router.get(
    "/documents",
    status_code=status.HTTP_200_OK,
)
async def list_documents():
    return {"documents": []}

