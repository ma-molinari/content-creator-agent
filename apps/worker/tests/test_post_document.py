"""Tests for the provisional structured post contract."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.post_document import PostDocumentV1


@pytest.fixture
def document():
    return {
        "schemaVersion": 1,
        "postType": "single",
        "slides": [{
            "id": "slide-1",
            "layout": "hero",
            "background": {"type": "solid", "color": "#172554"},
            "elements": [
                {"id": "title", "type": "text", "role": "heading", "content": "Olá, mundo!",
                 "style": {"color": "#FFFFFF", "size": "large"}},
                {"id": "cover", "type": "image", "assetId": "attachment-123", "fit": "cover"},
            ],
        }],
    }


def test_single_round_trip(document):
    parsed = PostDocumentV1.model_validate(document)
    assert parsed.slides[0].elements[1].asset_id == "attachment-123"
    assert PostDocumentV1.model_validate_json(parsed.model_dump_json(by_alias=True)) == parsed


def test_carousel_accepts_twenty_slides(document):
    document["postType"] = "carousel"
    document["slides"] = [deepcopy(document["slides"][0]) for _ in range(20)]
    for index, slide in enumerate(document["slides"]):
        slide["id"] = f"slide-{index}"
    assert len(PostDocumentV1.model_validate(document).slides) == 20


@pytest.mark.parametrize("change", [
    lambda d: d.update(schemaVersion=2),
    lambda d: d.update(schemaVersion=True),
    lambda d: d.update(postType="story"),
    lambda d: d.update(slides=[]),
    lambda d: d["slides"].append(deepcopy(d["slides"][0])),
    lambda d: d["slides"][0].update(layout="freeform"),
    lambda d: d["slides"][0]["background"].update(color="red"),
    lambda d: d["slides"][0]["elements"][0]["style"].update(font="external"),
    lambda d: d["slides"][0]["elements"][0].update(content="<script>alert(1)</script>"),
    lambda d: d["slides"][0]["elements"][0].update(content="https://example.com"),
    lambda d: d["slides"][0]["elements"][1].update(assetId="https://example.com/image.png"),
    lambda d: d["slides"][0]["elements"][1].update(assetId="../other-user"),
    lambda d: d["slides"][0]["elements"][1].update(css="background:red"),
    lambda d: d["slides"][0]["elements"][1].update(id="title"),
    lambda d: d["slides"][0]["elements"][0].update(content=" " * 10),
    lambda d: d["slides"][0]["elements"][0].update(content="a" * 2001),
    lambda d: d["slides"][0].update(elements=[]),
    lambda d: d.update(unexpected=True),
])
def test_invalid_documents_are_rejected(document, change):
    change(document)
    with pytest.raises(ValidationError):
        PostDocumentV1.model_validate(document)


def test_duplicate_slide_ids_rejected_in_carousel(document):
    document["postType"] = "carousel"
    document["slides"].append(deepcopy(document["slides"][0]))
    with pytest.raises(ValidationError):
        PostDocumentV1.model_validate(document)


def test_carousel_above_limit_rejected(document):
    document["postType"] = "carousel"
    document["slides"] = [deepcopy(document["slides"][0]) for _ in range(21)]
    for index, slide in enumerate(document["slides"]):
        slide["id"] = f"slide-{index}"
    with pytest.raises(ValidationError):
        PostDocumentV1.model_validate(document)
