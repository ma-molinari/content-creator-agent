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
        "reprompt_context": "",
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
    out = brief_text_for_edit(
        _state(optimized_brief="## Narrativa\n\nHello", reprompt_context="ignored"),
    )
    assert "Narrativa" in out
    assert "ignored" not in out


def test_brief_text_visual_only_omits_narrative_even_with_optimized() -> None:
    out = brief_text_for_edit(
        _state(
            refinement_scope="visual_only",
            optimized_brief="## Narrativa\n\nSecret",
            reprompt_context="thread",
        ),
    )
    assert "Contexto narrativo omitido" in out
    assert "Secret" not in out
    assert "thread" not in out


def test_brief_text_uses_preserve_directive_when_optimized_empty() -> None:
    out = brief_text_for_edit(
        _state(optimized_brief="", reprompt_context="  thread summary  "),
    )
    assert out == _EDIT_PRESERVE_BRIEF
    assert "thread summary" not in out


def test_brief_text_ignores_long_reprompt_when_optimized_empty() -> None:
    long_text = "a" * 50_000
    out = brief_text_for_edit(_state(optimized_brief="", reprompt_context=long_text))
    assert out == _EDIT_PRESERVE_BRIEF
