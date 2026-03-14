import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.deps import get_user_id_header
from app.schemas import ImportRequest, PostOut
from app.services.import_service import import_from_url

router = APIRouter(tags=["import"])


@router.post("/import", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def import_conversation(
    payload: ImportRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_user_id_header),
) -> PostOut:
    return await import_from_url(
        url=payload.url,
        user_id=user_id,
        session=session,
        background_tasks=background_tasks,
    )
