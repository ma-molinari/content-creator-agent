import pytest
from pydantic import ValidationError

from app.post_document_v2 import PostDocumentV2
from app.post_document_v3 import PostDocumentV3, promote_to_v3, used_asset_ids, validate_authorized_assets


def document():
    return {"schemaVersion": 3, "postType": "single", "palette": {"background": "#FFFFFF", "text": "#000000", "accent": "#000000"},
            "slides": [{"id": "s1", "layout": "hero", "background": {"type": "image", "assetId": "photo"},
                        "elements": [{"id": "t1", "type": "text", "role": "heading", "content": "Olá",
                                      "style": {"color": {"token": "text"}, "size": "large"}}]}],
            "credits": {"photo": {"title": "Paisagem", "creator": "Fotógrafa", "sourceUrl": "https://commons.wikimedia.org/wiki/File:Example",
                                  "license": "cc0", "licenseUrl": "https://creativecommons.org/publicdomain/zero/1.0/"}}}


def test_background_credit_and_asset_authorization():
    post = PostDocumentV3.model_validate(document())
    assert used_asset_ids(post) == {"photo"}
    validate_authorized_assets(post, {"photo"})
    with pytest.raises(ValueError):
        validate_authorized_assets(post, set())
    assert PostDocumentV3.model_validate_json(post.model_dump_json(by_alias=True)) == post


def test_unused_credit_and_unsafe_url_are_rejected():
    data = document()
    data["credits"]["other"] = data["credits"].pop("photo")
    with pytest.raises(ValidationError):
        PostDocumentV3.model_validate(data)
    data = document()
    data["credits"]["photo"]["sourceUrl"] = "javascript:alert(1)"
    with pytest.raises(ValidationError):
        PostDocumentV3.model_validate(data)


def test_promote_v2_preserves_base():
    data = document()
    data["schemaVersion"] = 2
    data.pop("credits")
    data["slides"][0]["background"] = {"type": "solid", "color": {"token": "background"}}
    before = PostDocumentV2.model_validate(data)
    after = promote_to_v3(before)
    assert before.schema_version == 2
    assert after.schema_version == 3
    assert after.slides[0].elements[0].content == before.slides[0].elements[0].content
    assert after.credits == {}
