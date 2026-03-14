from __future__ import annotations

import logging
import uuid

from sentence_transformers import SentenceTransformer
from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models import Post

logger = logging.getLogger("replyweave.embedding")


class EmbeddingService:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    def load(self) -> None:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)

    def embed_text(self, text: str) -> list[float]:
        if self._model is None:
            raise RuntimeError("Embedding model not loaded")
        vector = self._model.encode([text])[0]
        return vector.tolist()

    async def compute_and_store_embedding(self, post_id: uuid.UUID) -> None:
        async with async_session() as session:
            result = await session.execute(select(Post).where(Post.id == post_id))
            post = result.scalar_one_or_none()
            if not post or not post.conversation_summary:
                return
            embedding = self.embed_text(post.conversation_summary)
            post.embedding = embedding
            await session.commit()


embedding_service = EmbeddingService(model_name=settings.embedding_model_name)
