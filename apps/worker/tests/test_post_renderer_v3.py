from app.post_document_v3 import PostDocumentV3
from app.post_renderer_v3 import render_post_v3
from app.slide_design_checks import collect_design_violations
from tests.test_post_document_v3 import document


def test_image_background_has_opaque_text_surface_and_no_external_url():
    post = PostDocumentV3.model_validate(document())
    html = render_post_v3(post, {"photo"})[0]["html"]
    assert 'src="attachment://photo"' in html
    assert 'background:#FFFFFF' in html
    assert "position:absolute" in html
    assert not collect_design_violations(html)
