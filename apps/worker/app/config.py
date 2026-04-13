"""Application settings from environment."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# worker/app/config.py -> worker/
_WORKER_ROOT = Path(__file__).resolve().parent.parent
PROMPTS_DIR = _WORKER_ROOT / "prompts"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env",),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(..., min_length=1, description="OpenAI API key")
    aws_region: str = Field(..., min_length=1)
    aws_access_key_id: str = Field(..., min_length=1)
    aws_secret_access_key: str = Field(..., min_length=1)
    aws_s3_bucket: str = Field(..., min_length=1)
    go_api_url: str = Field(
        ...,
        min_length=1,
        description="Base URL of Go API, e.g. http://api:8080",
    )
    worker_api_key: str = Field(..., min_length=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
