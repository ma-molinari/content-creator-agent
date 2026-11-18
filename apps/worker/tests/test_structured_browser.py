"""Opt-in Chromium smoke tests with a locally supplied test font and no network."""

import asyncio
import base64
import os
from pathlib import Path

import pytest

from app.post_document import PostDocumentV1
from app.structured_render import render_structured_post

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
