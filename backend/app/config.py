from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://replyweave:replyweave@localhost:5432/replyweave"
    )
    embedding_model_name: str = Field(default="all-MiniLM-L6-v2")
    log_level: str = Field(default="INFO")


settings = Settings()
