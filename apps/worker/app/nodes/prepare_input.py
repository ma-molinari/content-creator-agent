"""Prepare normalized V2 worker input before security and LLM nodes."""

from __future__ import annotations

import logging
import re

from app.state import AgentState

logger = logging.getLogger(__name__)

_CHAT_SLIDE_MARKER = re.compile(r"(?i)###\s*SLIDE_FILE:[^\n]*")
_CHAT_END_SLIDE = re.compile(r"(?i)###\s*END_SLIDE\s*###")
_HTML_TAG = re.compile(r"<[^>]+>")


def _sanitize_message(text: str) -> str:
    text = _HTML_TAG.sub("", text or "")
    text = _CHAT_SLIDE_MARKER.sub("", text)
    text = _CHAT_END_SLIDE.sub("", text)
    lines = []
    for line in text.splitlines():
        if line.strip().startswith("---"):
            lines.append("> " + line)
        else:
            lines.append(line)
    return "\n".join(lines).strip()


def prepare_input(state: AgentState) -> dict[str, object]:
    logger.info("node=prepare_input job_id=%s", state.get("job_id"))
    raw = state.get("raw_message") or ""
    sanitized = _sanitize_message(raw)
    attachments = list(state.get("input_attachments") or [])
    if not attachments:
        attachments = [
            {
                "id": f"attachment-{idx + 1}",
                "s3_key": key,
                "mime_type": "image/jpeg",
                "sort_order": idx,
            }
            for idx, key in enumerate(state.get("user_attachment_s3_keys") or [])
        ]
    attachments.sort(key=lambda a: int(a.get("sort_order") or 0))
    return {
        "pipeline_version": "worker-v2-json-html",
        "raw_message": sanitized,
        "input": {
            "raw_message_original": raw,
            "sanitized_message": sanitized,
            "requested_slide_count": state.get("requested_slide_count"),
            "attachment_count": len(attachments),
        },
        "input_attachments": attachments,
        "user_attachment_s3_keys": [a.get("s3_key", "") for a in attachments if a.get("s3_key")],
    }
