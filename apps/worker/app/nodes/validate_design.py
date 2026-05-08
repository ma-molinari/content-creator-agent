"""V2 design validation wrapper around static HTML/CSS checks."""

from __future__ import annotations

import logging

from app.slide_design_checks import collect_design_violations
from app.state import AgentState, copy_errors

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3


def validate_design(state: AgentState) -> dict[str, object]:
    logger.info("node=validate_design job_id=%s", state.get("job_id"))
    diagnostics: list[str] = []
    prescription = f"{state.get('brand_text') or ''}\n{state.get('profile_text') or ''}\n{state.get('generation_plan') or ''}"
    for slide in state.get("slides_html") or []:
        fname = slide.get("filename") or "slide.html"
        for reason in collect_design_violations(slide.get("html") or "", prescription):
            diagnostics.append(f"validate_design: {fname}: {reason}")
    if not diagnostics:
        return {"errors": copy_errors(state), "design_retry_count": 0}
    retry = int(state.get("design_retry_count") or 0)
    report = {
        "category": "design",
        "actionable_messages": diagnostics,
        "design_retry_count": retry,
    }
    out: dict[str, object] = {
        "slides_html": [],
        "errors": copy_errors(state) + diagnostics,
        "validation_report": report,
    }
    if retry < _MAX_RETRIES:
        out["design_retry_count"] = retry + 1
    return out


def route_after_validate_design(state: AgentState) -> str:
    if state.get("slides_html"):
        return "continue"
    return "retry" if int(state.get("design_retry_count") or 0) < _MAX_RETRIES else "fail"
