import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.deps import get_user_id_header
from app.models import Like, Message, Post, User
from app.schemas import CursorPage, LikeResponse, MessageOut, PostCreate, PostListItem, PostOut, PostRemix
from app.services.import_service import create_post_from_conversation

router = APIRouter(prefix="/posts", tags=["posts"])


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


@router.post("", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreate,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_user_id_header),
) -> Post:
    return await create_post_from_conversation(
        conversation_json=payload.conversation_json,
        user_id=user_id,
        session=session,
        background_tasks=background_tasks,
        title=payload.title,
        source_platform=payload.source_platform,
        source_model=payload.source_model,
        language=payload.language,
    )


@router.get("", response_model=CursorPage)
async def list_posts(
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = None,
) -> CursorPage:
    query = select(Post)
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


@router.get("/{post_id}", response_model=PostOut)
async def get_post(post_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> Post:
    result = await session.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return post


@router.get("/{post_id}/messages", response_model=list[MessageOut])
async def get_post_messages(
    post_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[Message]:
    result = await session.execute(
        select(Message).where(Message.post_id == post_id).order_by(Message.position)
    )
    return result.scalars().all()


@router.post("/{post_id}/like", response_model=LikeResponse)
async def like_post(
    post_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_user_id_header),
) -> LikeResponse:
    user_result = await session.execute(select(User).where(User.id == user_id))
    if user_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown user")

    post_result = await session.execute(select(Post).where(Post.id == post_id))
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    like_result = await session.execute(
        select(Like).where(Like.user_id == user_id, Like.post_id == post_id)
    )
    if like_result.scalar_one_or_none() is None:
        session.add(Like(user_id=user_id, post_id=post_id))
        post.likes_count += 1
        await session.commit()
        await session.refresh(post)

    return LikeResponse(post_id=post.id, likes_count=post.likes_count)


@router.post("/{post_id}/remix", response_model=PostOut)
async def remix_post(
    post_id: uuid.UUID,
    payload: PostRemix,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    user_id: uuid.UUID = Depends(get_user_id_header),
) -> Post:
    result = await session.execute(select(Post).where(Post.id == post_id))
    original = result.scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    conversation_json = payload.conversation_json or original.conversation_json

    new_post = await create_post_from_conversation(
        conversation_json=conversation_json,
        user_id=user_id,
        session=session,
        background_tasks=background_tasks,
        title=payload.title or original.title,
        source_platform=original.source_platform,
        source_model=original.source_model,
        remix_of=original.id,
        language=payload.language or original.language,
    )

    original.remix_count += 1
    await session.commit()
    return new_post
