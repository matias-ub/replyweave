import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Post, User
from app.schemas import CursorPage, PostListItem, UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, session: AsyncSession = Depends(get_session)) -> User:
    user = User(username=payload.username)
    session.add(user)
    try:
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username taken") from exc
    await session.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> User:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    import base64

    raw = base64.urlsafe_b64decode(cursor.encode()).decode()
    created_at_raw, post_id_raw = raw.split("|", 1)
    created_at = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
    return created_at, uuid.UUID(post_id_raw)


def _encode_cursor(created_at: datetime, post_id: uuid.UUID) -> str:
    import base64

    raw = f"{created_at.isoformat()}|{post_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


@router.get("/{user_id}/posts", response_model=CursorPage)
async def list_user_posts(
    user_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = None,
) -> CursorPage:
    query = select(Post).where(Post.created_by == user_id)
    if cursor:
        created_at, post_id = _decode_cursor(cursor)
        query = query.where(tuple_(Post.created_at, Post.id) < (created_at, post_id))

    query = query.order_by(Post.created_at.desc(), Post.id.desc()).limit(limit)
    result = await session.execute(query)
    posts = result.scalars().all()
    next_cursor = None
    if len(posts) == limit:
        last = posts[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)

    return CursorPage(data=[PostListItem.model_validate(post) for post in posts], next_cursor=next_cursor)
