"""Tests for structured render validation and safe artifact handling."""

import asyncio

import pytest

from app.post_document import PostDocumentV1
from app.structured_render import render_structured_post


def document(text="Hello", image=False):
    elements = [{"id": "t", "type": "text", "role": "heading", "content": text, "style": {"color": "#FFFFFF", "size": "large", "font": "inter"}}]
    if image:
        elements.append({"id": "i", "type": "image", "assetId": "img", "fit": "cover"})
    return PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{
        "id": "s", "layout": "hero", "background": {"type": "solid", "color": "#123456"}, "elements": elements,
    }]})


class FakePage:
    def __init__(self, fonts=True, clipped=False):
        self.fonts, self.clipped = fonts, clipped
        self.html = ""
    async def route(self, *args): pass
    async def set_content(self, html, **kwargs): self.html = html
    async def evaluate(self, script, *args):
        if "document.fonts.load" in script: return self.fonts
        if "getBoundingClientRect" in script: return self.clipped
        return {"hadViolations": False}
    async def screenshot(self, **kwargs): return b"jpeg"
    async def close(self): pass


class FakeBrowser:
    def __init__(self, page): self.page = page
    async def new_page(self, **kwargs): return self.page
    async def close(self): pass


class FakePlaywright:
    def __init__(self, page): self.page = page
    async def __aenter__(self):
        self.chromium = self
        return self
    async def __aexit__(self, *args): pass
    async def launch(self, **kwargs): return FakeBrowser(self.page)


def setup(monkeypatch, page):
    monkeypatch.setattr("app.structured_render.async_playwright", lambda: FakePlaywright(page))
    async def wait(_page): pass
    monkeypatch.setattr("app.structured_render.wait_for_slide_images", wait)


def test_render_returns_html_and_jpeg_without_mutation(monkeypatch):
    page = FakePage()
    setup(monkeypatch, page)
    doc = document()
    before = doc.model_dump_json(by_alias=True)
    slides, images = asyncio.run(render_structured_post(doc, {}))
    assert slides[0]["filename"] == "slide_01.html"
    assert images[0]["jpeg_bytes"] == b"jpeg"
    assert before == doc.model_dump_json(by_alias=True)


@pytest.mark.parametrize("fonts,clipped,error", [(False, False, "font unavailable"), (True, True, "exceeds canvas")])
def test_font_or_overflow_failure_does_not_return_partial_output(monkeypatch, fonts, clipped, error):
    setup(monkeypatch, FakePage(fonts, clipped))
    with pytest.raises(ValueError, match=error):
        asyncio.run(render_structured_post(document(), {}))


def test_unknown_image_format_is_rejected_before_browser():
    with pytest.raises(ValueError, match="unsupported image"):
        asyncio.run(render_structured_post(document(image=True), {"img": b"not-an-image"}))


def test_missing_image_is_rejected_before_browser():
    with pytest.raises(ValueError, match="not authorized"):
        asyncio.run(render_structured_post(document(image=True), {}))


def test_identical_images_keep_distinct_references_after_contrast_fix(monkeypatch):
    doc = document(image=True)
    raw = doc.model_dump(mode="json", by_alias=True)
    raw["slides"][0]["elements"].append({"id": "i2", "type": "image", "assetId": "img2", "fit": "cover"})
    doc = PostDocumentV1.model_validate(raw)
    class ContrastPage(FakePage):
        async def evaluate(self, script, *args):
            if "document.fonts.load" in script: return True
            if "getBoundingClientRect" in script: return False
            return {"hadViolations": True}
        async def content(self): return self.html
    setup(monkeypatch, ContrastPage())
    png = b"\x89PNG\r\n\x1a\nexample"
    slides, _ = asyncio.run(render_structured_post(doc, {"img": png, "img2": png}))
    assert 'src="attachment://img"' in slides[0]["html"]
    assert 'src="attachment://img2"' in slides[0]["html"]
