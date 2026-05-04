"""Tests for brief context in edit_slides refinement path."""

from __future__ import annotations

from app.nodes.edit_slides import _EDIT_PRESERVE_BRIEF, brief_text_for_edit


def _state(**kwargs: object) -> dict:
    base = {
        "job_id": "j",
        "user_id": "u",
        "chat_id": "c",
        "raw_message": "",
        "audit_text": "",
        "brand_text": "",
        "profile_text": "",
        "optimized_brief": "",
        "raw_slide_output": "",
        "slides_html": [],
        "rendered_slides": [],
        "artifacts": [],
        "retry_count": 0,
        "errors": [],
    }
    base.update(kwargs)
    return base


def test_brief_text_prefers_optimized_brief() -> None:
    out = brief_text_for_edit(_state(optimized_brief="## Narrativa\n\nHello"))
    assert "Narrativa" in out


def test_brief_text_visual_only_omits_narrative_even_with_optimized() -> None:
    out = brief_text_for_edit(
        _state(
            refinement_scope="visual_only",
            optimized_brief="## Narrativa\n\nSecret",
        ),
    )
    assert "Contexto narrativo omitido" in out
    assert "Secret" not in out


def test_brief_text_mixed_scope_keeps_optimized_brief() -> None:
    out = brief_text_for_edit(
        _state(refinement_scope="mixed", optimized_brief="## Narrativa\n\nKeep me"),
    )
    assert "Keep me" in out
