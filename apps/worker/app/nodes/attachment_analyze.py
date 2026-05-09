"""Build a structured attachment plan from user-uploaded images."""

from __future__ import annotations

import logging
import re

from app.nodes.describe_user_attachments import describe_user_attachments
from app.state import AgentState

logger = logging.getLogger(__name__)

_SLIDE_DEST_RE = re.compile(r"(?:slide|p[áa]gina)\s*(\d{1,2})", re.I)
_ORDINAL_DEST_RE = re.compile(
    r"\b(?:(primeir[oa]|segund[oa]|terceir[oa]|quart[oa]|quint[oa])\s+(?:slide|p[áa]gina)|"
    r"(?:slide|p[áa]gina)\s+(primeir[oa]|segund[oa]|terceir[oa]|quart[oa]|quint[oa]))\b",
    re.I,
)
_ORDINAL_SLIDE_NUMBERS = {
    "primeiro": 1,
    "primeira": 1,
    "segundo": 2,
    "segunda": 2,
    "terceiro": 3,
    "terceira": 3,
    "quarto": 4,
    "quarta": 4,
    "quinto": 5,
    "quinta": 5,
}


def _requested_slide_for_attachment(raw: str) -> int | None:
    m = _SLIDE_DEST_RE.search(raw or "")
    if m:
        try:
            return int(m.group(1))
        except ValueError:
            return None
    ordinal = _ORDINAL_DEST_RE.search(raw or "")
    if ordinal:
        word = (ordinal.group(1) or ordinal.group(2) or "").strip().lower()
        return _ORDINAL_SLIDE_NUMBERS.get(word)
    return None


async def attachment_analyze(state: AgentState) -> dict[str, object]:
    logger.info("node=attachment_analyze job_id=%s", state.get("job_id"))
    attachments = list(state.get("input_attachments") or [])
    if not attachments:
        return {"attachment_plan": []}
    described = await describe_user_attachments(state)
    urls = list(described.get("user_attachment_signed_urls") or [])
    descs = list(described.get("user_attachment_descriptions") or [])
    mimes = list(described.get("user_attachment_mime_types") or [])
    dest = _requested_slide_for_attachment(state.get("raw_message") or "")
    plan = []
    for i, att in enumerate(attachments):
        att_id = str(att.get("id") or f"attachment-{i + 1}")
        required_slide_number = dest if dest is not None else None
        plan.append(
            {
                "id": att_id,
                "s3_key": str(att.get("s3_key") or ""),
                "render_ref": f"attachment://{att_id}",
                "url": urls[i] if i < len(urls) else "",
                "mime_type": mimes[i] if i < len(mimes) else str(att.get("mime_type") or "image/jpeg"),
                "description": descs[i] if i < len(descs) else "",
                "required_slide_number": required_slide_number,
                "suggested_slide_number": 1 if dest is None and i == 0 else None,
                "role": "explicit" if dest is not None else ("cover_visual" if i == 0 else "supporting_visual"),
            }
        )
    out = dict(described)
    out["attachment_plan"] = plan
    return out
