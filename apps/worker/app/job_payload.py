"""Worker dispatch payload normalization."""

from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, field_validator, model_validator
from typing_extensions import Self

from app.slide_count_inference import infer_requested_slide_count
from app.state import AgentState


class DispatchPayload(BaseModel):
    post_format: Literal["legacy_html", "structured_v1"] = "legacy_html"
    target_schema_version: Optional[Literal[1, 2, 3]] = None
    generation_mode: Optional[Literal["create", "edit"]] = None
    base_version_id: Optional[UUID] = None
    document_s3_key: str = ""
    job_id: UUID
    user_id: UUID
    chat_id: UUID
    message_id: Optional[UUID] = None
    chat_post_type: Optional[str] = None
    authorized_asset_sources: Optional[dict[str, str]] = None
    reference_asset_sources: Optional[dict[str, str]] = None
    raw_message: str = ""
    audit_text: str = ""
    brand_text: str = ""
    reference_s3_keys: Optional[list[str]] = None
    # HTML slide sources from last assistant turn (Go API); used to detect edit vs full regen.
    existing_slide_html_s3_keys: Optional[list[str]] = None
    existing_slide_html: Optional[list[dict[str, object]]] = None
    user_attachment_s3_keys: Optional[list[str]] = None
    user_attachments: Optional[list[dict[str, object]]] = None
    known_attachments: Optional[list[dict[str, object]]] = None
    expects_slide_refinement: bool = False
    # Optional: quando a API enviar N explícito; senão o worker infere a partir de raw_message.
    requested_slide_count: Optional[int] = None


    @field_validator("target_schema_version", mode="before")
    @classmethod
    def strict_target_schema(cls, value: object) -> object:
        if value is not None and type(value) is not int:
            raise ValueError("target schema must be an integer")
        return value

    @model_validator(mode="after")
    def validate_mode(self) -> Self:
        if self.post_format == "structured_v1":
            if self.generation_mode not in {"create", "edit"}:
                raise ValueError("structured mode is required")
            if self.generation_mode == "edit" and (self.base_version_id is None or not self.document_s3_key):
                raise ValueError("structured edit requires a base document")
        return self


def initial_state(payload: DispatchPayload) -> AgentState:
    n: Optional[int] = payload.requested_slide_count
    if n is None:
        n = infer_requested_slide_count(payload.raw_message)
    return {
        "job_id": str(payload.job_id),
        "post_format": payload.post_format,
        "target_schema_version": payload.target_schema_version or 1,
        "generation_mode": payload.generation_mode,
        "base_version_id": str(payload.base_version_id) if payload.base_version_id else "",
        "document_s3_key": payload.document_s3_key,
        "user_id": str(payload.user_id),
        "chat_id": str(payload.chat_id),
        "message_id": str(payload.message_id) if payload.message_id else "",
        "chat_post_type": payload.chat_post_type or "",
        "authorized_asset_sources": dict(payload.authorized_asset_sources or {}),
        "reference_asset_sources": dict(payload.reference_asset_sources) if payload.reference_asset_sources is not None else None,
        "raw_message": payload.raw_message,
        "audit_text": payload.audit_text,
        "brand_text": payload.brand_text,
        "reference_s3_keys": list(payload.reference_s3_keys or []),
        "existing_slide_html_s3_keys": list(payload.existing_slide_html_s3_keys or []),
        "user_attachment_s3_keys": list(payload.user_attachment_s3_keys or []),
        "input_attachments": [
            {
                "id": str(a.get("id") or ""),
                "s3_key": str(a.get("s3_key") or ""),
                "mime_type": str(a.get("mime_type") or "image/jpeg"),
                "sort_order": int(a.get("sort_order") or 0),
            }
            for a in (payload.user_attachments or [])
        ],
        "known_attachments": [
            {
                "id": str(a.get("id") or ""),
                "s3_key": str(a.get("s3_key") or ""),
                "mime_type": str(a.get("mime_type") or "image/jpeg"),
                "sort_order": int(a.get("sort_order") or 0),
            }
            for a in (payload.known_attachments or [])
        ],
        "existing_slide_sources": [
            {
                "slide_number": int(s.get("slide_number") or 0),
                "html_s3_key": str(s.get("html_s3_key") or ""),
            }
            for s in (payload.existing_slide_html or [])
        ],
        "existing_slide_html": [],
        "expects_slide_refinement": bool(payload.expects_slide_refinement),
        "is_refinement": False,
        "requested_slide_count": n,
        "profile_text": "",
        "optimized_brief": "",
        "raw_slide_output": "",
        "slides_html": [],
        "rendered_slides": [],
        "artifacts": [],
        "retry_count": 0,
        "brief_retry_count": 0,
        "errors": [],
    }
