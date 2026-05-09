"""Worker dispatch payload normalization."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.slide_count_inference import infer_requested_slide_count
from app.state import AgentState


class DispatchPayload(BaseModel):
    job_id: UUID
    user_id: UUID
    chat_id: UUID
    message_id: Optional[UUID] = None
    chat_post_type: Optional[str] = None
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


def initial_state(payload: DispatchPayload) -> AgentState:
    n: Optional[int] = payload.requested_slide_count
    if n is None:
        n = infer_requested_slide_count(payload.raw_message)
    return {
        "job_id": str(payload.job_id),
        "user_id": str(payload.user_id),
        "chat_id": str(payload.chat_id),
        "message_id": str(payload.message_id) if payload.message_id else "",
        "chat_post_type": payload.chat_post_type or "",
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
