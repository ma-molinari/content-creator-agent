"""Atomic V2 operations preserve unspecified values and reject invalid edits."""

from copy import deepcopy

import pytest

from app.post_document_v2 import PostDocumentV2
from app.post_operations_v2 import apply_operations_v2


@pytest.fixture
def base():
    return PostDocumentV2.model_validate({"schemaVersion": 2, "postType": "single",
        "palette": {"background": "#FFFFFF", "text": "#000000", "accent": "#FF0000"},
        "slides": [{"id": "s1", "layout": "hero", "background": {"type": "solid", "color": {"token": "background"}},
                    "elements": [{"id": "title", "type": "text", "role": "heading", "content": "Original",
                                  "style": {"color": {"hex": "#000000"}, "size": "large"}}]}]})


def bar():
    return {"id": "bar", "type": "decoration", "kind": "bar", "color": {"token": "accent"},
            "width": "full", "thickness": "medium", "corner": "rounded"}


def test_insert_update_palette_and_remove_preserve_other_fields(base):
    before = deepcopy(base.model_dump(mode="json", by_alias=True))
    result = apply_operations_v2(base, [
        {"op": "insert_decoration", "slideId": "s1", "afterElementId": None, "decoration": bar()},
        {"op": "update_decoration", "slideId": "s1", "elementId": "bar", "changes": {"width": "short"}},
        {"op": "set_palette_color", "token": "accent", "color": "#0000FF"},
    ], set())
    assert [e.id for e in result.slides[0].elements] == ["bar", "title"]
    assert result.slides[0].elements[0].width == "short"
    assert result.slides[0].elements[0].corner == "rounded"
    assert result.slides[0].elements[1].model_dump(mode="json", by_alias=True) == before["slides"][0]["elements"][0]
    assert base.model_dump(mode="json", by_alias=True) == before
    removed = apply_operations_v2(result, [{"op": "remove_decoration", "slideId": "s1", "elementId": "bar"}], set())
    assert [e.id for e in removed.slides[0].elements] == ["title"]


@pytest.mark.parametrize("operations", [
    [{"op": "set_palette_color", "token": "accent", "color": "#0000FF"}],
    [{"op": "insert_decoration", "slideId": "s1", "afterElementId": "missing", "decoration": bar()}],
    [{"op": "insert_decoration", "slideId": "s1", "afterElementId": None, "decoration": dict(bar(), id="title")}],
    [{"op": "remove_decoration", "slideId": "s1", "elementId": "title"}],
    [{"op": "set_text_style", "slideId": "s1", "elementId": "title", "style": {"color": {"hex": "#111111"}, "size": "large"}}],
    [{"op": "set_text", "slideId": "s1", "elementId": "title", "content": "Alterado"},
     {"op": "remove_decoration", "slideId": "s1", "elementId": "missing"}],
    [{"op": "insert_decoration", "slideId": "s1", "afterElementId": None, "decoration": bar()},
     {"op": "update_decoration", "slideId": "s1", "elementId": "bar", "changes": {"kind": "line"}}],
    [{"op": "insert_decoration", "slideId": "s1", "afterElementId": None, "decoration": bar()},
     {"op": "update_decoration", "slideId": "s1", "elementId": "bar", "changes": {"color": None}}],
])
def test_invalid_operations_leave_base_untouched(base, operations):
    before = base.model_dump_json(by_alias=True)
    with pytest.raises(ValueError):
        apply_operations_v2(base, operations, set())
    assert base.model_dump_json(by_alias=True) == before


def test_thirteen_elements_rejected_without_removing_content(base):
    raw = base.model_dump(mode="json", by_alias=True)
    raw["slides"][0]["elements"] = [dict(deepcopy(raw["slides"][0]["elements"][0]), id=f"t{i}") for i in range(12)]
    full = PostDocumentV2.model_validate(raw)
    with pytest.raises(ValueError):
        apply_operations_v2(full, [{"op": "insert_decoration", "slideId": "s1", "afterElementId": "t0", "decoration": bar()}], set())
    assert len(full.slides[0].elements) == 12


def test_insert_image_requires_authorization(base):
    operation = {"op": "insert_image", "slideId": "s1", "afterElementId": "title", "image":
                 {"id": "new-image", "type": "image", "assetId": "ref", "fit": "contain"}}
    result = apply_operations_v2(base, [operation], {"ref"})
    assert result.slides[0].elements[1].asset_id == "ref"
    with pytest.raises(ValueError, match="authorized"):
        apply_operations_v2(base, [operation], set())


def test_structurally_valid_operation_cannot_prove_user_intent(base):
    # The planner can still choose a valid operation that misinterprets a request.
    result = apply_operations_v2(base, [{"op": "set_text", "slideId": "s1", "elementId": "title", "content": "Outro texto"}], set())
    assert result.slides[0].elements[0].content == "Outro texto"
