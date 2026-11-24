"""Opt-in Chromium smoke tests with a locally supplied test font and no network."""

import asyncio
import base64
import os
import re
from pathlib import Path

import pytest

from app.post_document import PostDocumentV1
from app.post_document_v3 import PostDocumentV3
from app.structured_render import render_structured_post
from tests.test_post_document_v3 import document as v3_document

pytestmark = pytest.mark.skipif(os.getenv("RUN_CHROMIUM_TESTS") != "1", reason="requires Chromium and TEST_FONT_PATH")


def make_document(content):
    return PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{
        "id": "slide", "layout": "hero", "background": {"type": "solid", "color": "#000000"},
        "elements": [
            {"id": "title", "type": "text", "role": "heading", "content": content, "style": {"color": "#ffffff", "size": "large", "font": "inter"}},
            {"id": "picture", "type": "image", "assetId": "asset1", "fit": "cover"},
        ],
    }]})


def test_chromium_loads_image_and_rejects_overflow(monkeypatch):
    font = base64.b64encode(Path(os.environ["TEST_FONT_PATH"]).read_bytes()).decode("ascii")
    css = "@font-face{font-family:Inter;src:url(data:font/ttf;base64," + font + ") format('truetype');}"

    async def local_font_only(route):
        if route.request.url.startswith("https://fonts.googleapis.com/"):
            await route.fulfill(status=200, content_type="text/css", body=css)
        elif route.request.url.startswith("data:"):
            await route.continue_()
        else:
            await route.abort()

    monkeypatch.setattr("app.structured_render._allow_font_route", local_font_only)
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/aXcAAAAASUVORK5CYII=")
    slides, images = asyncio.run(render_structured_post(make_document("Ideias que merecem ser compartilhadas"), {"asset1": png}))
    assert images[0]["jpeg_bytes"].startswith(b"\xff\xd8\xff")
    assert 'src="attachment://asset1"' in slides[0]["html"]
    with pytest.raises(ValueError, match="exceeds canvas"):
        asyncio.run(render_structured_post(make_document("Conteúdo longo " * 120), {"asset1": png}))


def test_chromium_rejects_missing_font(monkeypatch):
    async def no_font(route):
        if route.request.url.startswith("https://fonts.googleapis.com/"):
            await route.fulfill(status=200, content_type="text/css", body="/* unavailable */")
        else:
            await route.abort()

    monkeypatch.setattr("app.structured_render._allow_font_route", no_font)
    doc = make_document("Título").model_dump(mode="json", by_alias=True)
    doc["slides"][0]["elements"] = doc["slides"][0]["elements"][:1]
    with pytest.raises(ValueError, match="font unavailable"):
        asyncio.run(render_structured_post(PostDocumentV1.model_validate(doc), {}))


def test_chromium_renders_v3_background(monkeypatch):
    font = base64.b64encode(Path(os.environ["TEST_FONT_PATH"]).read_bytes()).decode("ascii")
    css = "@font-face{font-family:'Plus Jakarta Sans';src:url(data:font/ttf;base64," + font + ") format('truetype');}"

    async def local_font_only(route):
        if route.request.url.startswith("https://fonts.googleapis.com/"):
            await route.fulfill(status=200, content_type="text/css", body=css)
        elif route.request.url.startswith("data:"):
            await route.continue_()
        else:
            await route.abort()

    monkeypatch.setattr("app.structured_render._allow_font_route", local_font_only)
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/aXcAAAAASUVORK5CYII=")
    slides, images = asyncio.run(render_structured_post(PostDocumentV3.model_validate(v3_document()), {"photo": png}))
    assert images[0]["jpeg_bytes"].startswith(b"\xff\xd8\xff")
    assert 'src="attachment://photo"' in slides[0]["html"]

    async def measure_card():
        from playwright.async_api import async_playwright
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(args=["--disable-background-networking", "--disable-extensions", "--no-default-browser-check"])
            try:
                page = await browser.new_page(viewport={"width": 1080, "height": 1350})
                await page.route("**/*", local_font_only)
                html = slides[0]["html"].replace("attachment://photo", "data:image/png;base64," + base64.b64encode(png).decode())
                await page.set_content(html, wait_until="load")
                return await page.evaluate("""() => {
                    const main = document.querySelector('main');
                    const box = main.getBoundingClientRect();
                    return {height: box.height, width: box.width, background: getComputedStyle(main).backgroundColor};
                }""")
            finally:
                await browser.close()

    card = asyncio.run(measure_card())
    assert card["width"] * card["height"] < 1080 * 1350 * 0.5
    assert card["background"].startswith("rgba(255, 255, 255,")

    long_doc = v3_document()
    long_doc["slides"][0]["elements"][0]["content"] = "Conteúdo longo " * 120
    with pytest.raises(ValueError, match="exceeds canvas"):
        asyncio.run(render_structured_post(PostDocumentV3.model_validate(long_doc), {"photo": png}))


def test_v3_places_text_away_from_focal_area(monkeypatch):
    font = base64.b64encode(Path(os.environ["TEST_FONT_PATH"]).read_bytes()).decode("ascii")
    css = "@font-face{font-family:'Plus Jakarta Sans';src:url(data:font/ttf;base64," + font + ") format('truetype');}"

    async def local_font_only(route):
        if route.request.url.startswith("https://fonts.googleapis.com/"):
            await route.fulfill(status=200, content_type="text/css", body=css)
        elif route.request.url.startswith("data:"):
            await route.continue_()
        else:
            await route.abort()

    monkeypatch.setattr("app.structured_render._allow_font_route", local_font_only)
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/aXcAAAAASUVORK5CYII=")
    for box, moved in [({"left": 20, "top": 5, "right": 80, "bottom": 35}, True),
                       ({"left": 20, "top": 70, "right": 80, "bottom": 95}, False)]:
        raw = v3_document()
        raw["slides"][0]["background"]["focalBox"] = box
        slides, _ = asyncio.run(render_structured_post(PostDocumentV3.model_validate(raw), {"photo": png}))
        placement = re.search(r"transform: translate\(([-\d.]+)px, ([-\d.]+)px\)", slides[0]["html"])
        assert placement is not None
        assert (float(placement.group(2)) > 0) == moved
        assert 'src="attachment://photo"' in slides[0]["html"]


def test_v3_adjusts_wide_image_crop_toward_focal_area(monkeypatch):
    from playwright.async_api import async_playwright
    font = base64.b64encode(Path(os.environ["TEST_FONT_PATH"]).read_bytes()).decode("ascii")
    css = "@font-face{font-family:'Plus Jakarta Sans';src:url(data:font/ttf;base64," + font + ") format('truetype');}"

    async def local_font_only(route):
        if route.request.url.startswith("https://fonts.googleapis.com/"):
            await route.fulfill(status=200, content_type="text/css", body=css)
        elif route.request.url.startswith("data:"):
            await route.continue_()
        else:
            await route.abort()

    async def make_wide_png():
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()
            try:
                page = await browser.new_page()
                return await page.evaluate("""() => {
                    const canvas = document.createElement('canvas'); canvas.width = 200; canvas.height = 100;
                    canvas.getContext('2d').fillRect(0, 0, 200, 100);
                    return canvas.toDataURL('image/png').split(',')[1];
                }""")
            finally:
                await browser.close()

    monkeypatch.setattr("app.structured_render._allow_font_route", local_font_only)
    png = base64.b64decode(asyncio.run(make_wide_png()))
    raw = v3_document()
    raw["slides"][0]["background"]["focalBox"] = {"left": 75, "top": 15, "right": 95, "bottom": 60}
    slides, _ = asyncio.run(render_structured_post(PostDocumentV3.model_validate(raw), {"photo": png}))
    assert 'object-position: 100% 50%' in slides[0]["html"]
