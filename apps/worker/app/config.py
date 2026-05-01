"""Application settings from environment."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

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
    # Chat model for optimize_prompt and generate_slides.
    openai_chat_model: str = Field(default="gpt-5.4-mini", min_length=1)
    # Vision model for optional design reference images in describe_references.
    reference_vision_model: str = Field(default="gpt-5.4-mini", min_length=1)
    # Max bytes loaded per reference image from S3 (aligned with API upload cap for refs).
    reference_image_max_bytes: int = Field(default=5_242_880, ge=262_144, le=52_428_800)
    # Dynamic max output tokens for generate_slides: min(base + per_slide * N, cap).
    generate_slides_tokens_base: int = Field(default=1500, ge=500)
    generate_slides_tokens_per_slide: int = Field(default=1200, ge=200)
    generate_slides_max_tokens_cap: int = Field(default=16_000, ge=2_000)
    # If set, overrides the computed value (still capped at generate_slides_max_tokens_cap).
    generate_slides_max_tokens: Optional[int] = Field(default=None)
    # Max combined length (characters) of raw_message + reprompt_context before LLM nodes.
    user_prompt_max_chars: int = Field(default=48_000, ge=4096)


@lru_cache
def get_settings() -> Settings:
    return Settings()
