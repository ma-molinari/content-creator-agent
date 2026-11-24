import re
import pytest

from app.post_document_v3 import PostDocumentV3
from app.post_renderer_v2 import _luminance
from app.post_renderer_v3 import _transparent_surface, render_post_v3
from app.slide_design_checks import collect_design_violations
from tests.test_post_document_v3 import document


def test_image_background_has_opaque_text_surface_and_no_external_url():
    post = PostDocumentV3.model_validate(document())
    html = render_post_v3(post, {"photo"})[0]["html"]
    assert 'src="attachment://photo"' in html
    assert 'background:rgba(255,255,255,' in html
    assert "position:absolute" in html
    assert not collect_design_violations(html)


@pytest.mark.parametrize("background,text", [("#FFFFFF", "#000000"), ("#000000", "#FFFFFF"), ("#F5EADF", "#202020")])
def test_transparency_meets_contrast_on_black_and_white_images(background, text):
    data = document()
    data["palette"]["background"] = background
    data["palette"]["text"] = text
    post = PostDocumentV3.model_validate(data)
    surface = _transparent_surface(post, post.slides[0])
    r, g, b, alpha = (float(value) for value in re.fullmatch(r"rgba\((\d+),(\d+),(\d+),([\d.]+)\)", surface).groups())
    assert alpha < 1
    for underlying in (0, 255):
        composite = "#" + "".join(f"{round(value * alpha + underlying * (1 - alpha)):02x}" for value in (r, g, b))
        a, b_lum = sorted((_luminance(text), _luminance(composite)), reverse=True)
        assert (a + 0.05) / (b_lum + 0.05) >= 4.5


def test_rejects_when_transparency_cannot_guarantee_contrast():
    data = document()
    data["palette"]["text"] = "#767676"
    post = PostDocumentV3.model_validate(data)
    with pytest.raises(ValueError, match="transparent background"):
        _transparent_surface(post, post.slides[0])
