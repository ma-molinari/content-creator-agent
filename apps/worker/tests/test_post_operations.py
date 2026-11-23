"""Tests for atomic structured editing."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.post_document import PostDocumentV1
from app.post_operations import apply_operations


@pytest.fixture
def base():
    return PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{
        "id": "s1", "layout": "hero", "background": {"type": "solid", "color": "#000000"},
        "elements": [
            {"id": "title", "type": "text", "role": "heading", "content": "Original", "style": {"color": "#FFFFFF", "size": "large"}},
            {"id": "image", "type": "image", "assetId": "original", "fit": "cover"},
        ],
    }]})


def test_background_change_preserves_other_fields_and_base(base):
    before = deepcopy(base.model_dump(by_alias=True))
    result = apply_operations(base, [{"op": "set_background", "slideId": "s1", "background": {"type": "solid", "color": "#123456"}}], set())
    expected = deepcopy(before)
    expected["slides"][0]["background"]["color"] = "#123456"
    assert result.model_dump(by_alias=True) == expected
    assert base.model_dump(by_alias=True) == before


def test_all_edit_types(base):
    result = apply_operations(base, [
        {"op": "set_text", "slideId": "s1", "elementId": "title", "content": "Novo"},
        {"op": "set_text_style", "slideId": "s1", "elementId": "title", "style": {"color": "#AAAAAA", "size": "small"}},
        {"op": "set_layout", "slideId": "s1", "layout": "quote"},
        {"op": "set_image", "slideId": "s1", "elementId": "image", "assetId": "new", "fit": "contain"},
    ], {"new"})
    assert result.slides[0].layout == "quote"
    assert result.slides[0].elements[0].content == "Novo"
    assert result.slides[0].elements[1].asset_id == "new"


def test_insert_image_is_atomic_and_authorized(base):
    operation = {"op": "insert_image", "slideId": "s1", "afterElementId": "title", "image":
                 {"id": "ref-image", "type": "image", "assetId": "ref", "fit": "contain"}}
    result = apply_operations(base, [operation], {"ref"})
    assert [item.id for item in result.slides[0].elements] == ["title", "ref-image", "image"]
    assert len(base.slides[0].elements) == 2
    with pytest.raises(ValueError, match="authorized"):
        apply_operations(base, [operation], set())


@pytest.mark.parametrize("operations", [
    [],
    [{"op": "delete_slide", "slideId": "s1"}],
    [{"op": "set_layout", "slideId": "missing", "layout": "hero"}],
    [{"op": "set_text", "slideId": "s1", "elementId": "image", "content": "x"}],
    [{"op": "set_image", "slideId": "s1", "elementId": "image", "assetId": "foreign", "fit": "cover"}],
    [{"op": "set_text", "slideId": "s1", "elementId": "title", "content": "<script>x</script>"}],
    [{"op": "set_layout", "slideId": "s1", "layout": "hero", "other": 1}],
    [{"op": "set_layout", "slideId": "s1", "layout": "quote"}, {"op": "set_text", "slideId": "missing", "elementId": "title", "content": "x"}],
])
def test_invalid_operations_leave_base_untouched(base, operations):
    before = deepcopy(base.model_dump(by_alias=True))
    with pytest.raises((ValueError, ValidationError)):
        apply_operations(base, operations, set())
    assert base.model_dump(by_alias=True) == before
