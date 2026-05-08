"""Create the canonical plan consumed by slide generation/editing prompts."""

from __future__ import annotations

import logging

from app.state import AgentState

logger = logging.getLogger(__name__)


def build_generation_plan(state: AgentState) -> dict[str, object]:
    logger.info("node=build_generation_plan job_id=%s", state.get("job_id"))
    intent = state.get("intent_result") or {"kind": "new", "scope": None}
    requested = state.get("requested_slide_count")
    attachment_plan = list(state.get("attachment_plan") or [])
    plan = {
        "mode": intent.get("kind") or "new",
        "scope": intent.get("scope"),
        "raw_message": state.get("raw_message") or "",
        "profile_overview": state.get("profile_overview") or {},
        "requested_slide_count": requested,
        "chat_post_type": state.get("chat_post_type") or "",
        "attachment_requirements": [
            {
                "id": a.get("id"),
                "url": a.get("url"),
                "description": a.get("description"),
                "required_slide_number": a.get("required_slide_number"),
                "role": a.get("role"),
                "usage_rule": (
                    "mandatory_exact_url_on_required_slide"
                    if a.get("required_slide_number")
                    else "use_when_relevant"
                ),
                "composition_rule": (
                    "Use as a visible, prominent design element on the required slide. "
                    "Prefer hero image, full-bleed background with overlay, large editorial crop, "
                    "or a framed image occupying meaningful canvas area. Do not create a placeholder label."
                    if a.get("required_slide_number")
                    else "Use as supporting visual only when it strengthens the slide narrative."
                ),
            }
            for a in attachment_plan
        ],
        "design_direction": {
            "quality_bar": "premium Instagram editorial carousel, not wireframe",
            "layout": "single strong hero per slide, controlled spacing, no empty panels",
            "image_integration": "attachments must be real visible pixels, integrated with overlays/crops/frames when required",
            "avoid": [
                "placeholder text such as imagem em anexo",
                "tiny unused thumbnails",
                "blank boxes where an image should be",
                "large decorative panels without editorial content",
            ],
        },
        "existing_slide_count": len(state.get("existing_slide_html") or []),
        "html_rules": [
            "Return valid JSON only.",
            "Each slide html must be a complete document with <html> and </html>.",
            "Canvas must be 1080px wide and 1350px tall.",
            "No JavaScript or inline event handlers.",
            "Remote assets allowed only for Google Fonts and provided S3 attachment URLs.",
            "When an attachment has required_slide_number, include its exact attachment_requirements.url in that slide HTML.",
            "Do not satisfy image requirements with labels/placeholders; the URL must appear in an img src/srcset or CSS background-image.",
        ],
    }
    return {"generation_plan": plan}
