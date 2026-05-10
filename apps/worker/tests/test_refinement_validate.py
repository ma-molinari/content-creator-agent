"""Tests for visual copy preservation (visual_only refinement scope)."""

from __future__ import annotations

from app.refinement_validate import (
    existing_slides_index,
    visible_text_normalized,
    visual_copy_preserved,
)
from app.state import SlideItem


def test_visible_text_normalized_strips_style_and_collapses_whitespace() -> None:
    html = """<html><head><style>.x{color:red}</style></head><body>
    <p>  Hello


    World  </p></body></html>"""
    assert visible_text_normalized(html) == "Hello\nWorld"


def test_visual_copy_preserved_css_only_change() -> None:
    old = """<html><body style="margin:0"><div>Oi</div></body></html>"""
    new = """<html><body style="margin:0"><div style="color:#ff00ff">Oi</div></body></html>"""
    idx = {"slide_01.html": old}
    parsed: list[SlideItem] = [{"filename": "slide_01.html", "html": new}]
    ok, errs = visual_copy_preserved(idx, parsed)
    assert ok is True
    assert errs == []


def test_visual_copy_preserved_detects_text_change() -> None:
    old = """<html><body><p>Alpha</p></body></html>"""
    new = """<html><body><p>Beta</p></body></html>"""
    idx = {"slide_01.html": old}
    parsed: list[SlideItem] = [{"filename": "slide_01.html", "html": new}]
    ok, errs = visual_copy_preserved(idx, parsed)
    assert ok is False
    assert len(errs) == 1
    assert "copy_preservation:" in errs[0]
    assert "slide_01.html" in errs[0]


def test_existing_slides_index_lower_keys() -> None:
    slides: list[SlideItem] = [{"filename": "Slide_01.HTML", "html": "<html>a</html>"}]
    idx = existing_slides_index(slides)
    assert "slide_01.html" in idx


def test_validate_slide_package_visual_only_blocks_visible_text_change() -> None:
    """visual_only refinement must not pass when visible copy diverges."""
    from app.nodes.validate_slide_package import validate_slide_package

    old_html = (
        "<html><head><meta charset=\"utf-8\"><title>s</title></head>"
        "<body style=\"margin:0;width:1080px;height:1350px;\"><p>Alpha label</p></body></html>"
    )
    new_html = (
        "<html><head><meta charset=\"utf-8\"><title>s</title></head>"
        "<body style=\"margin:0;width:1080px;height:1350px;\"><p>Beta label</p></body></html>"
    )
    state: dict = {
        "job_id": "j",
        "slide_package": {"slides": [{"filename": "slide_01.html", "html": new_html}]},
        "retry_count": 0,
        "errors": [],
        "requested_slide_count": 1,
        "is_refinement": True,
        "refinement_scope": "visual_only",
        "existing_slide_html": [{"filename": "slide_01.html", "html": old_html}],
    }
    out = validate_slide_package(state)  # type: ignore[arg-type]
    assert out.get("slides_html") == []
    assert int(out.get("retry_count") or 0) == 1
    errs = out.get("errors") or []
    assert any("copy_preservation:" in (e or "") for e in errs)


def test_validate_slide_package_visual_only_allows_css_only_edit() -> None:
    from app.nodes.validate_slide_package import validate_slide_package

    old_html = (
        "<html><head><meta charset=\"utf-8\"><title>s</title></head>"
        "<body style=\"margin:0;width:1080px;height:1350px;background:#fff;\">"
        "<p>Same</p></body></html>"
    )
    new_html = (
        "<html><head><meta charset=\"utf-8\"><title>s</title></head>"
        "<body style=\"margin:0;width:1080px;height:1350px;background:#ff00ff;\">"
        "<p>Same</p></body></html>"
    )
    state: dict = {
        "job_id": "j",
        "slide_package": {"slides": [{"filename": "slide_01.html", "html": new_html}]},
        "retry_count": 0,
        "errors": [],
        "requested_slide_count": 1,
        "is_refinement": True,
        "refinement_scope": "visual_only",
        "existing_slide_html": [{"filename": "slide_01.html", "html": old_html}],
    }
    out = validate_slide_package(state)  # type: ignore[arg-type]
    slides = out.get("slides_html") or []
    assert len(slides) == 1
    assert "retry_count" not in out


def test_validate_slide_package_layout_blocks_visible_text_change() -> None:
    from app.nodes.validate_slide_package import validate_slide_package

    old_html = (
        "<html><head><meta charset=\"utf-8\"><title>s</title></head>"
        "<body style=\"margin:0;width:1080px;height:1350px;\"><p>Conteúdo original</p></body></html>"
    )
    new_html = (
        "<html><head><meta charset=\"utf-8\"><title>s</title></head>"
        "<body style=\"margin:0;width:1080px;height:1350px;\"><p>Explicando a melhoria de layout</p></body></html>"
    )
    state: dict = {
        "job_id": "j",
        "slide_package": {"slides": [{"filename": "slide_01.html", "html": new_html}]},
        "retry_count": 0,
        "errors": [],
        "requested_slide_count": 1,
        "is_refinement": True,
        "refinement_scope": "layout",
        "existing_slide_html": [{"filename": "slide_01.html", "html": old_html}],
    }
    out = validate_slide_package(state)  # type: ignore[arg-type]
    assert out.get("slides_html") == []
    assert int(out.get("retry_count") or 0) == 1
    errs = out.get("errors") or []
    assert any("copy_preservation:" in (e or "") for e in errs)
