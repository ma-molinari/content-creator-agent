import pytest

from app.post_document_v3 import ImageCreditV3, PostDocumentV3
from app.stock_edits import set_stock_background
from tests.test_post_document_v3 import document


def test_replacing_background_preserves_original_and_credit_history():
    before = PostDocumentV3.model_validate(document())
    credit = ImageCreditV3.model_validate({"title": "Outra foto", "sourceUrl": "https://commons.wikimedia.org/other",
                                           "license": "cc0", "licenseUrl": "https://creativecommons.org/publicdomain/zero/1.0/"})
    after = set_stock_background(before, slide_id="s1", asset_id="new", credit=credit, authorized_assets={"photo", "new"})
    assert before.slides[0].background.asset_id == "photo"
    assert set(before.credits) == {"photo"}
    assert after.slides[0].background.asset_id == "new"
    assert set(after.credits) == {"new"}
    assert after.slides[0].elements == before.slides[0].elements
    with pytest.raises(ValueError, match="not authorized"):
        set_stock_background(before, slide_id="s1", asset_id="new", credit=credit, authorized_assets={"photo"})


def test_replacing_one_of_two_uses_preserves_both_credits():
    data = document()
    data["postType"] = "carousel"
    data["slides"].append({**data["slides"][0], "id": "s2"})
    before = PostDocumentV3.model_validate(data)
    credit = before.credits["photo"]
    after = set_stock_background(before, slide_id="s1", asset_id="new", credit=credit, authorized_assets={"photo", "new"})
    assert set(after.credits) == {"photo", "new"}
    assert after.slides[1].background.asset_id == "photo"
