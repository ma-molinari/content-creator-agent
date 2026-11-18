"""Structured renderer tests."""

import pytest

from app.post_document import PostDocumentV1
from app.post_renderer import RENDERER_VERSION, render_post


def make_document(layout="hero", content="A & B"):
    return PostDocumentV1.model_validate({
        "schemaVersion": 1, "postType": "single", "slides": [{
            "id": "slide-1", "layout": layout,
            "background": {"type": "solid", "color": "#172554"},
            "elements": [
                {"id": "title", "type": "text", "role": "heading", "content": content,
                 "style": {"color": "#FFFFFF", "size": "large"}},
                {"id": "image", "type": "image", "assetId": "asset-1", "fit": "cover"},
            ],
        }],
    })


@pytest.mark.parametrize("layout", ["hero", "editorial", "quote"])
def test_each_layout_renders_deterministically(layout):
    doc = make_document(layout)
    slides = render_post(doc, {"asset-1"})
    assert slides == render_post(doc, {"asset-1"})
    assert slides[0]["filename"] == "slide_01.html"
    assert f'class="{layout}"' in slides[0]["html"]
    assert "A &amp; B" in slides[0]["html"]
    assert 'src="attachment://asset-1"' in slides[0]["html"]
    assert RENDERER_VERSION


def test_unauthorized_asset_is_rejected():
    with pytest.raises(ValueError, match="not authorized"):
        render_post(make_document(), set())


def test_mutated_document_is_revalidated():
    doc = make_document()
    doc.slides.clear()
    with pytest.raises(ValueError):
        render_post(doc, {"asset-1"})


def test_text_is_escaped_even_for_non_tag_angle_brackets():
    html = render_post(make_document(content='2 < 3 & "x"'), {"asset-1"})[0]["html"]
    assert '2 &lt; 3 &amp; &quot;x&quot;' in html


def test_default_html_passes_existing_static_design_checks():
    from app.slide_design_checks import collect_design_violations

    assert collect_design_violations(render_post(make_document(), {"asset-1"})[0]["html"]) == []
