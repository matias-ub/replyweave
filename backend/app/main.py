import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import import_routes, posts, search, users
from app.services.embedding_service import embedding_service

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("replyweave")

app = FastAPI(title="replyweave")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(posts.router)
app.include_router(import_routes.router)
app.include_router(search.router)


@app.on_event("startup")
def load_embedding_model() -> None:
    logger.info("Loading embedding model")
    embedding_service.load()
    logger.info("Embedding model ready")
