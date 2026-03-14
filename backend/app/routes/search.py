import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Post
from app.schemas import PostListItem, SearchResponse
from app.services.embedding_service import embedding_service

router = APIRouter(tags=["search"])


@router.get("/search/posts", response_model=SearchResponse)
async def search_posts(
    q: str = Query(min_length=1),
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=20, ge=1, le=50),
) -> SearchResponse:
    query_embedding = embedding_service.embed_text(q)
    result = await session.execute(
        select(Post)
        .where(Post.embedding.is_not(None))
        .order_by(Post.embedding.l2_distance(query_embedding))
        .limit(limit)
    )
    posts = result.scalars().all()
    return SearchResponse(data=[PostListItem.model_validate(post) for post in posts])


@router.get("/posts/{post_id}/similar", response_model=SearchResponse)
async def similar_posts(
    post_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    limit: int = Query(default=10, ge=1, le=50),
) -> SearchResponse:
    result = await session.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    if post.embedding is None:
        return SearchResponse(data=[])

    result = await session.execute(
        select(Post)
        .where(Post.embedding.is_not(None))
        .where(Post.id != post.id)
        .order_by(Post.embedding.l2_distance(post.embedding))
        .limit(limit)
    )
    posts = result.scalars().all()
    return SearchResponse(data=[PostListItem.model_validate(post) for post in posts])
