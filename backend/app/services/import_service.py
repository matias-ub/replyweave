import uuid
from typing import Any

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message, Post, User
from app.services.conversation_parser import (
    detect_language,
    estimate_tokens,
    extract_messages,
    extract_prompt,
    extract_summary,
)
from app.services.embedding_service import embedding_service
from app.normalizers.chatgpt_normalizer import normalize_chatgpt
from app.normalizers.claude_normalizer import normalize_claude


def _detect_platform(url: str) -> str:
    if "chatgpt.com/share/" in url:
        return "chatgpt"
    if "claude.ai/share/" in url:
        return "claude"
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported URL")


def _mock_fixture(platform: str) -> dict[str, Any]:
    # TODO: Production should use a headless browser (Playwright) to extract JS payloads.
    if platform == "chatgpt":
        return {
            "messages": [
                {
                    "id": "msg1",
                    "role": "user",
                    "content": [{"type": "text", "text": "Explain recursion like I'm 10"}],
                },
                {
                    "id": "msg2",
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "Imagine a box that contains another box."}
                    ],
                },
            ]
        }
    return {
        "messages": [
            {
                "id": "msg1",
                "role": "user",
                "content": [{"type": "text", "text": "What is the capital of France?"}],
            },
            {
                "id": "msg2",
                "role": "assistant",
                "content": [{"type": "text", "text": "Paris is the capital of France."}],
            },
        ]
    }


async def create_post_from_conversation(
    *,
    conversation_json: dict[str, Any],
    user_id: uuid.UUID,
    session: AsyncSession,
    background_tasks: BackgroundTasks,
    title: str | None = None,
    source_platform: str | None = None,
    source_model: str | None = None,
    remix_of: uuid.UUID | None = None,
    language: str | None = None,
) -> Post:
    user_result = await session.execute(select(User).where(User.id == user_id))
    if user_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown user")

    messages = extract_messages(conversation_json)
    prompt = extract_prompt(messages)
    summary = extract_summary(messages)
    message_count = len(messages)
    token_estimate = estimate_tokens(messages)
    detected_language = language or detect_language(messages)

    post = Post(
        title=title,
        prompt=prompt,
        conversation_summary=summary,
        conversation_json=conversation_json,
        source_platform=source_platform,
        source_model=source_model,
        remix_of=remix_of,
        created_by=user_id,
        message_count=message_count,
        token_estimate=token_estimate,
        language=detected_language,
    )
    session.add(post)
    await session.flush()

    for msg in messages:
        session.add(
            Message(
                post_id=post.id,
                role=msg.role,
                content=msg.content,
                position=msg.position,
            )
        )

    await session.commit()
    await session.refresh(post)

    background_tasks.add_task(embedding_service.compute_and_store_embedding, post.id)
    return post


async def import_from_url(
    *,
    url: str,
    user_id: uuid.UUID,
    session: AsyncSession,
    background_tasks: BackgroundTasks,
) -> Post:
    platform = _detect_platform(url)
    raw = _mock_fixture(platform)

    if platform == "chatgpt":
        normalized = normalize_chatgpt(raw)
    else:
        normalized = normalize_claude(raw)

    return await create_post_from_conversation(
        conversation_json=normalized,
        user_id=user_id,
        session=session,
        background_tasks=background_tasks,
        source_platform=platform,
        source_model="mock",
    )
