"""LangGraph agent state and typed payloads."""

from typing import Optional, TypedDict

from typing_extensions import NotRequired


class SlideItem(TypedDict):
    filename: str
    html: str


class RenderedSlide(TypedDict):
    filename: str
    jpeg_bytes: bytes


class ArtifactRef(TypedDict):
    s3_key: str
    slide_number: int


class AgentState(TypedDict):
    job_id: str
    user_id: str
    chat_id: str
    raw_message: str
    audit_text: str
    brand_text: str
    reprompt_context: str
    profile_text: str
    optimized_brief: str
    raw_slide_output: str
    slides_html: list[SlideItem]
    rendered_slides: list[RenderedSlide]
    artifacts: list[ArtifactRef]
    retry_count: int
    errors: list[str]
    # Optional user-facing caption / summary for chat (set in finalize)
    assistant_text: NotRequired[str]
    # S3 object keys (design ref images) resolved by the API; empty = skip vision step
    reference_s3_keys: NotRequired[list[str]]
    # Explicit slide count: inferência no worker, ou payload da API. None = sem exigência de N.
    requested_slide_count: NotRequired[Optional[int]]
    # Set by prompt_security_validate when input fails deterministic checks (routing + finalize).
    prompt_validation_failed: NotRequired[bool]
    # Internal rule id for logs when validation rejects (not shown to end users).
    prompt_security_rule: NotRequired[str]
