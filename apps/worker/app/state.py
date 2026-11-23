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
    html_s3_key: NotRequired[Optional[str]]


class InputAttachment(TypedDict):
    id: str
    s3_key: str
    mime_type: str
    sort_order: int


class ExistingSlideSource(TypedDict):
    slide_number: int
    html_s3_key: str


class SecurityResult(TypedDict):
    ok: bool
    reason: NotRequired[str]
    blocked_fields: NotRequired[list[str]]


class IntentResult(TypedDict):
    kind: str
    scope: NotRequired[Optional[str]]
    confidence: str
    requires_existing_html: bool
    reason: str


class AttachmentPlanItem(TypedDict):
    id: str
    s3_key: str
    render_ref: NotRequired[str]
    url: str
    mime_type: str
    description: str
    required_slide_number: NotRequired[Optional[int]]
    role: str


class SlidePackageSlide(TypedDict):
    filename: str
    slide_number: int
    html: str
    used_attachment_ids: NotRequired[list[str]]


class SlidePackage(TypedDict):
    assistant_text: str
    slides: list[SlidePackageSlide]
    layout_notes: NotRequired[str]
    attachment_usage: NotRequired[list[dict]]


class AgentState(TypedDict):
    authorized_asset_sources: NotRequired[dict[str, str]]
    post_format: NotRequired[str]
    target_schema_version: NotRequired[int]
    generation_mode: NotRequired[Optional[str]]
    base_version_id: NotRequired[str]
    document_s3_key: NotRequired[str]
    job_id: str
    user_id: str
    chat_id: str
    raw_message: str
    audit_text: str
    brand_text: str
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
    # Set by security_validate when input fails deterministic checks (routing + finalize).
    prompt_validation_failed: NotRequired[bool]
    # Internal rule id for logs when validation rejects (not shown to end users).
    prompt_security_rule: NotRequired[str]
    # Retained for callback metadata compatibility with older worker runs.
    brief_retry_count: NotRequired[int]
    # Failed validate_design retries before giving up (separate from retry_count / package validation).
    design_retry_count: NotRequired[int]
    # Iterative refinement: HTML S3 keys from API, loaded HTML, and edit vs generate path.
    existing_slide_html_s3_keys: NotRequired[list[str]]
    user_attachment_s3_keys: NotRequired[list[str]]
    user_attachment_descriptions: NotRequired[list[str]]
    user_attachment_intent: NotRequired[str]
    user_attachment_signed_urls: NotRequired[list[str]]
    user_attachment_mime_types: NotRequired[list[str]]
    existing_slide_html: NotRequired[list[SlideItem]]
    is_refinement: NotRequired[bool]
    # iterative refinement: visual_only | copy | layout | mixed (from intent_detect)
    refinement_scope: NotRequired[str]
    # API: chat already had assistant slides before this job — must use edit path or fail clearly.
    expects_slide_refinement: NotRequired[bool]
    # load_existing_slides: cannot load HTML for a required refinement — route early to finalize.
    refinement_context_unavailable: NotRequired[bool]
    # V2 structured pipeline fields.
    pipeline_version: NotRequired[str]
    message_id: NotRequired[str]
    chat_post_type: NotRequired[str]
    input: NotRequired[dict]
    input_attachments: NotRequired[list[InputAttachment]]
    known_attachments: NotRequired[list[InputAttachment]]
    existing_slide_sources: NotRequired[list[ExistingSlideSource]]
    profile_overview: NotRequired[dict]
    security_result: NotRequired[SecurityResult]
    intent_result: NotRequired[IntentResult]
    attachment_plan: NotRequired[list[AttachmentPlanItem]]
    generation_plan: NotRequired[dict]
    slide_package: NotRequired[SlidePackage]
    validation_report: NotRequired[dict]
    worker_metadata: NotRequired[dict]


def copy_errors(state: AgentState) -> list[str]:
    return list(state.get("errors") or [])
