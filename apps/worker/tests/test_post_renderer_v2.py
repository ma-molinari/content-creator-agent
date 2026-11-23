"""V2 visual catalog, contrast, and deterministic browser output."""

import asyncio
import base64
import os
import logging
from pathlib import Path

import pytest
from playwright.async_api import async_playwright

from app.post_document import PostDocumentV1
from app.post_document_v2 import PostDocumentV2, promote_v1
from app.post_renderer_v2 import render_post_v2
from app.structured_render import render_structured_post


def document():
    return PostDocumentV2.model_validate({"schemaVersion": 2, "postType": "single",
        "palette": {"background": "#FFFFFF", "text": "#000000", "accent": "#F26930"},
        "slides": [{"id": "s", "layout": "hero", "background": {"type": "solid", "color": {"token": "background"}},
        "elements": [{"id": "bar", "type": "decoration", "kind": "bar", "color": {"token": "accent"},
                      "width": "full", "thickness": "medium", "corner": "rounded"},
                     {"id": "text", "type": "text", "role": "heading", "content": "Ideias criativas",
                      "style": {"color": {"token": "text"}, "size": "large", "font": "inter"}}]}]})


@pytest.mark.parametrize("width,expected", [("short", "25%"), ("medium", "50%"), ("full", "100%")])
@pytest.mark.parametrize("thickness,height", [("thin", 4), ("medium", 12), ("thick", 24)])
@pytest.mark.parametrize("layout", ["hero", "editorial", "quote"])
def test_catalog_dimensions_and_order(width, expected, thickness, height, layout):
    raw = document().model_dump(mode="json", by_alias=True)
    raw["slides"][0]["layout"] = layout
    raw["slides"][0]["elements"][0].update(width=width, thickness=thickness)
    html = render_post_v2(PostDocumentV2.model_validate(raw), set())[0]["html"]
    assert f"width:{expected};height:{height}px;border-radius:{height / 2:g}px;background:#F26930" in html
    assert html.index('class="element decoration"') < html.index('class="element text')


def test_low_contrast_rejected_without_mutating_snapshot(caplog):
    raw = document().model_dump(mode="json", by_alias=True)
    raw["palette"]["text"] = "#CCCCCC"
    doc = PostDocumentV2.model_validate(raw)
    before = doc.model_dump_json(by_alias=True)
    caplog.set_level(logging.INFO)
    with pytest.raises(ValueError, match="contrast"):
        asyncio.run(render_structured_post(doc, {}))
    assert doc.model_dump_json(by_alias=True) == before
    assert "event=structured_validation" in caplog.text and "reason=contrast" in caplog.text
    assert "Ideias criativas" not in caplog.text


def test_line_with_literal_color_and_square_corner():
    raw = document().model_dump(mode="json", by_alias=True)
    raw["slides"][0]["elements"][0].update(kind="line", color={"hex": "#123456"}, corner="square")
    html = render_post_v2(PostDocumentV2.model_validate(raw), set())[0]["html"]
    assert "height:12px;border-radius:0px;background:#123456" in html


def test_promotion_keeps_literals_when_palette_changes():
    base = PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{
        "id": "s", "layout": "hero", "background": {"type": "solid", "color": "#FFFFFF"},
        "elements": [{"id": "t", "type": "text", "role": "body", "content": "Olá", "style": {"color": "#000000", "size": "small"}}]}]})
    raw = promote_v1(base).model_dump(mode="json", by_alias=True)
    raw["palette"]["text"] = "#FFFFFF"
    assert "color:#000000" in render_post_v2(PostDocumentV2.model_validate(raw), set())[0]["html"]


@pytest.mark.skipif(os.getenv("RUN_CHROMIUM_TESTS") != "1", reason="requires Chromium and TEST_FONT_PATH")
def test_browser_outputs_snapshot_colors_and_detects_overflow(monkeypatch):
    font = base64.b64encode(Path(os.environ["TEST_FONT_PATH"]).read_bytes()).decode("ascii")
    css = "@font-face{font-family:Inter;src:url(data:font/ttf;base64," + font + ") format('truetype');}"

    async def local_font(route):
        if route.request.url.startswith("https://fonts.googleapis.com/"):
            await route.fulfill(status=200, content_type="text/css", body=css)
        elif route.request.url.startswith("data:"):
            await route.continue_()
        else:
            await route.abort()

    monkeypatch.setattr("app.structured_render._allow_font_route", local_font)
    doc = document()
    before = doc.model_dump_json(by_alias=True)
    slides, images = asyncio.run(render_structured_post(doc, {}))
    assert "background:#F26930" in slides[0]["html"]
    assert images[0]["jpeg_bytes"].startswith(b"\xff\xd8\xff")
    assert doc.model_dump_json(by_alias=True) == before

    async def inspect_jpeg(data):
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page()
                return await page.evaluate("""async data => {
                    const image = new Image(); image.src = 'data:image/jpeg;base64,' + data;
                    await image.decode();
                    const canvas = document.createElement('canvas');
                    canvas.width = image.width; canvas.height = image.height;
                    const context = canvas.getContext('2d'); context.drawImage(image, 0, 0);
                    return [image.width, image.height, ...context.getImageData(200, 101, 1, 1).data];
                }""", base64.b64encode(data).decode("ascii"))
            finally:
                await browser.close()

    width, height, red, green, blue, _ = asyncio.run(inspect_jpeg(images[0]["jpeg_bytes"]))
    assert (width, height) == (1080, 1350)
    assert abs(red - 242) < 15 and abs(green - 105) < 15 and abs(blue - 48) < 15

    raw = doc.model_dump(mode="json", by_alias=True)
    raw["slides"][0]["elements"].append({"id": "i", "type": "image", "assetId": "asset-1", "fit": "contain"})
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/aXcAAAAASUVORK5CYII=")
    with_image, _ = asyncio.run(render_structured_post(PostDocumentV2.model_validate(raw), {"asset-1": png}))
    assert 'src="attachment://asset-1"' in with_image[0]["html"]
    raw = doc.model_dump(mode="json", by_alias=True)
    raw["slides"][0]["elements"][1]["content"] = "Conteúdo longo " * 120
    with pytest.raises(ValueError, match="exceeds canvas"):
        asyncio.run(render_structured_post(PostDocumentV2.model_validate(raw), {}))
