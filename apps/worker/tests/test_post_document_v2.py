"""Shared V2 contract cases and lossless promotion behavior."""

from copy import deepcopy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.post_document import PostDocumentV1
from app.post_document_v2 import PostDocumentV2, promote_v1, validate_authorized_assets


CASES = json.loads((Path(__file__).resolve().parents[3] / "tests/fixtures/structured_documents_v2.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_shared_v2_contract(case):
    if case["valid"]:
        document = PostDocumentV2.model_validate(case["document"])
        assert PostDocumentV2.model_validate_json(document.model_dump_json(by_alias=True)) == document
    else:
        with pytest.raises(ValidationError):
            PostDocumentV2.model_validate(case["document"])


def test_promotion_preserves_multislide_content_and_defaults():
    raw = {"schemaVersion": 1, "postType": "carousel", "slides": [
        {"id": "s1", "layout": "hero", "background": {"type": "solid", "color": "#123456"},
         "elements": [{"id": "image", "type": "image", "assetId": "asset-1", "fit": "cover"}]},
        {"id": "s2", "layout": "quote", "background": {"type": "solid", "color": "#ffffff"},
         "elements": [{"id": f"t{i}", "type": "text", "role": "body", "content": "Exemplo",
                       "style": {"color": "#000001", "size": "small"}} for i in range(12)]},
    ]}
    before = deepcopy(raw)
    base = PostDocumentV1.model_validate(raw)
    promoted = promote_v1(base).model_dump(mode="json", by_alias=True)
    assert raw == before
    assert base.model_dump(mode="json", by_alias=True)["slides"][1]["elements"][0]["style"]["font"] == "plus_jakarta_sans"
    assert promoted["palette"] == {"background": "#123456", "text": "#000001", "accent": "#000001"}
    assert promoted["slides"][0]["elements"] == before["slides"][0]["elements"]
    assert len(promoted["slides"][1]["elements"]) == 12
    assert promoted["slides"][1]["elements"][0]["style"]["color"] == {"hex": "#000001"}


def test_promotion_without_text_and_asset_authorization():
    base = PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{
        "id": "s1", "layout": "editorial", "background": {"type": "solid", "color": "#ffffff"},
        "elements": [{"id": "i1", "type": "image", "assetId": "asset-1", "fit": "contain"}],
    }]})
    promoted = promote_v1(base)
    assert promoted.palette.text == promoted.palette.accent == "#000000"
    validate_authorized_assets(promoted, {"asset-1"})
    with pytest.raises(ValueError, match="not authorized"):
        validate_authorized_assets(promoted, set())
