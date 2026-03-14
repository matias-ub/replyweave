import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    created_at: datetime

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: uuid.UUID
    post_id: uuid.UUID
    role: str
    content: str
    position: int
    created_at: datetime

    class Config:
        from_attributes = True


class PostCreate(BaseModel):
    title: str | None = None
    conversation_json: dict[str, Any]
    source_platform: str | None = None
    source_model: str | None = None
    language: str | None = None


class PostRemix(BaseModel):
    title: str | None = None
    conversation_json: dict[str, Any] | None = None
    language: str | None = None


class PostOut(BaseModel):
    id: uuid.UUID
    title: str | None
    prompt: str | None
    conversation_summary: str | None
    conversation_json: dict[str, Any]
    source_platform: str | None
    source_model: str | None
    remix_of: uuid.UUID | None
    created_by: uuid.UUID
    created_at: datetime
    likes_count: int
    comments_count: int
    remix_count: int
    message_count: int
    token_estimate: int
    language: str | None

    class Config:
        from_attributes = True


class PostListItem(BaseModel):
    id: uuid.UUID
    title: str | None
    prompt: str | None
    conversation_summary: str | None
    source_platform: str | None
    source_model: str | None
    remix_of: uuid.UUID | None
    created_by: uuid.UUID
    created_at: datetime
    likes_count: int
    comments_count: int
    remix_count: int
    message_count: int
    token_estimate: int
    language: str | None

    class Config:
        from_attributes = True


class ImportRequest(BaseModel):
    url: str


class CursorPage(BaseModel):
    data: list[PostListItem]
    next_cursor: str | None


class SearchResponse(BaseModel):
    data: list[PostListItem]


class LikeResponse(BaseModel):
    post_id: uuid.UUID
    likes_count: int


class RemixResponse(BaseModel):
    post: PostOut
