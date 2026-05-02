"""Validate slide HTML/CSS against static design rules before JPEG render.

Runs after ``parse_validate`` and before ``render_to_jpeg``. Failures emit messages
prefixed with ``design_validate:`` for inclusion in ``generate_slides`` retry feedback.

Retry budget mirrors ``parse_validate`` (three incremental failures before finalize).
"""

from __future__ import annotations

import logging

from app.slide_design_checks import collect_design_violations
from app.state import AgentState, copy_errors

logger = logging.getLogger(__name__)

# Matches parse_validate: three increments on failure → fourth routing sees ≥3 and fails.
_DESIGN_RETRY_CEILING = 3


def design_validate(state: AgentState) -> dict:
    logger.info("node=design_validate job_id=%s", state.get("job_id"))
    slides = state.get("slides_html") or []
    errors = copy_errors(state)
    prescription_blob = f"{state.get('brand_text') or ''}\n{state.get('optimized_brief') or ''}"

    diagnostics: list[str] = []
    for item in slides:
        html = item.get("html") or ""
        fname = item.get("filename") or "slide.html"
        for reason in collect_design_violations(html, prescription_blob):
            diagnostics.append(f"design_validate: {fname}: {reason}")

    if not diagnostics:
        return {"design_retry_count": 0, "errors": errors}

    merged = errors + diagnostics
    design_retry_count = int(state.get("design_retry_count") or 0)

    if design_retry_count < _DESIGN_RETRY_CEILING:
        logger.info(
            "node=design_validate job_id=%s failures=%s design_retry_count=%s→%s",
            state.get("job_id"),
            len(diagnostics),
            design_retry_count,
            design_retry_count + 1,
        )
        return {
            "slides_html": [],
            "errors": merged,
            "design_retry_count": design_retry_count + 1,
        }

    logger.info(
        "node=design_validate job_id=%s failures=%s giving_up",
        state.get("job_id"),
        len(diagnostics),
    )
    return {"slides_html": [], "errors": merged}


def route_after_design(state: AgentState) -> str:
    """Return ``retry``, ``continue``, or ``fail`` for conditional edges from design_validate."""
    slides = state.get("slides_html") or []
    if slides:
        return "continue"
    if int(state.get("design_retry_count") or 0) < _DESIGN_RETRY_CEILING:
        return "retry"
    return "fail"
