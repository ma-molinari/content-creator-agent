"""Validate structured slide package and convert it to renderable SlideItem rows."""

from __future__ import annotations

import logging

from app.refinement_validate import existing_slides_index, visual_copy_preserved
from app.state import AgentState, SlideItem, copy_errors

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3


def _valid_html(html: str) -> bool:
    h = (html or "").strip().lower()
    return len(h) >= 80 and "<html" in h and "</html>" in h


def validate_slide_package(state: AgentState) -> dict[str, object]:
    logger.info("node=validate_slide_package job_id=%s", state.get("job_id"))
    package = state.get("slide_package") or {}
    slides = list(package.get("slides") or [])
    errors = copy_errors(state)
    diagnostics: list[str] = []
    valid: list[SlideItem] = []
    expected = state.get("requested_slide_count")

    if not isinstance(slides, list) or not slides:
        diagnostics.append("slide_package: nenhum slide válido no JSON.")
    for idx, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            diagnostics.append(f"slide_package: item {idx} não é objeto.")
            continue
        fname = str(slide.get("filename") or f"slide_{idx:02d}.html")
        if not fname.endswith(".html"):
            fname += ".html"
        html = str(slide.get("html") or "")
        if not _valid_html(html):
            diagnostics.append(f"slide_package: {fname}: HTML inválido/truncado.")
            continue
        valid.append({"filename": fname, "html": html})

    if isinstance(expected, int) and len(valid) != expected:
        diagnostics.append(f"slide_package: esperados {expected} slides; recebidos {len(valid)}.")

    if (
        state.get("is_refinement")
        and (state.get("refinement_scope") or "").strip().lower() == "visual_only"
        and valid
    ):
        ok, copy_errs = visual_copy_preserved(
            existing_slides_index(state.get("existing_slide_html")),
            valid,
        )
        if not ok:
            diagnostics.extend(copy_errs)

    if diagnostics:
        retry = int(state.get("retry_count") or 0)
        report = {
            "category": "slide_package",
            "actionable_messages": diagnostics,
            "retry_count": retry,
        }
        out: dict[str, object] = {
            "slides_html": [],
            "errors": errors + diagnostics,
            "validation_report": report,
        }
        if retry < _MAX_RETRIES:
            out["retry_count"] = retry + 1
        return out

    return {
        "slides_html": valid,
        "validation_report": {"category": "slide_package", "actionable_messages": [], "retry_count": state.get("retry_count") or 0},
        "errors": errors,
    }


def route_after_slide_package(state: AgentState) -> str:
    if state.get("slides_html"):
        return "continue"
    return "retry" if int(state.get("retry_count") or 0) < _MAX_RETRIES else "fail"
