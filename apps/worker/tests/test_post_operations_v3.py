from app.post_document_v3 import PostDocumentV3
from app.post_operations_v3 import apply_operations_v3
from tests.test_post_document_v3 import document


def test_edit_text_preserves_background_and_credit():
    before = PostDocumentV3.model_validate(document())
    result = apply_operations_v3(before, [{"op": "set_text", "slideId": "s1", "elementId": "t1", "content": "Novo"}], {"photo"})
    assert result.slides[0].elements[0].content == "Novo"
    assert result.slides[0].background == before.slides[0].background
    assert result.credits == before.credits
    assert before.slides[0].elements[0].content == "Olá"


def test_explicit_solid_background_removes_unused_image_credit():
    before = PostDocumentV3.model_validate(document())
    result = apply_operations_v3(before, [{"op": "set_background", "slideId": "s1", "background": {"type": "solid", "color": {"token": "background"}}}], {"photo"})
    assert result.slides[0].background.type == "solid"
    assert result.credits == {}
    assert before.credits
