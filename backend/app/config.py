from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://replyweave:replyweave@localhost:5432/replyweave"
    )
    embedding_model_name: str = Field(default="all-MiniLM-L6-v2")
    log_level: str = Field(default="INFO")
    importer_timeout_seconds: int = Field(default=25)
    importer_user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    )


settings = Settings()
