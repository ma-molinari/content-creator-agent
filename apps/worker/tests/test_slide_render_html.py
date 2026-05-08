"""Tests for slide HTML injection before JPEG export."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from app.nodes.render_and_contrast import _render_one
from app.slide_asset_wait import wait_for_slide_images
from app.slide_render_html import enhance_slide_html_for_render


class TestEnhanceSlideHtmlForRender(unittest.TestCase):
    def test_inserts_after_head(self) -> None:
        html = "<!DOCTYPE html><html><head><meta charset='utf-8'></head><body>x</body></html>"
        out = enhance_slide_html_for_render(html)
        self.assertIn("preconnect", out)
        self.assertIn("__pipeline_slide_typography", out)
        self.assertIn("font-optical-sizing", out)
        self.assertLess(out.index("preconnect"), out.index("<meta"))

    def test_head_with_attributes(self) -> None:
        html = "<html><HEAD lang=pt></head><body></body></html>"
        out = enhance_slide_html_for_render(html)
        self.assertIn("fonts.googleapis.com", out)

    def test_inserts_layout_safety_before_body_close(self) -> None:
        html = "<!DOCTYPE html><html><head></head><body><div>x</div></body></html>"
        out = enhance_slide_html_for_render(html)
        self.assertIn("__pipeline_layout_safety", out)
        self.assertLess(out.index("__pipeline_layout_safety"), out.index("</body>"))
        self.assertIn("justify-content:flex-start!important", out)

    def test_empty_passthrough(self) -> None:
        self.assertEqual(enhance_slide_html_for_render(""), "")


class FakeAssetWaitPage:
    def __init__(self, result: object) -> None:
        self.result = result

    async def evaluate(self, expression: str, arg: object = None) -> object:
        return self.result


class TestWaitForSlideImages(unittest.IsolatedAsyncioTestCase):
    async def test_accepts_successful_asset_wait(self) -> None:
        page = FakeAssetWaitPage({"ok": True, "total": 2, "failed": []})
        await wait_for_slide_images(page, timeout_ms=100)

    async def test_reports_background_image_failure(self) -> None:
        page = FakeAssetWaitPage(
            {
                "ok": False,
                "total": 1,
                "failed": [
                    {
                        "kind": "background-image",
                        "url": "https://bucket.s3.us-east-1.amazonaws.com/users/u/chat-attachments/a.jpg",
                    }
                ],
            }
        )
        with self.assertRaisesRegex(RuntimeError, "background-image"):
            await wait_for_slide_images(page, timeout_ms=100)


class FakeRenderPage:
    def __init__(self) -> None:
        self.closed = False
        self.wait_finished = False
        self.screenshot_after_wait = False

    async def set_viewport_size(self, viewport: dict[str, int]) -> None:
        self.viewport = viewport

    async def route(self, pattern: str, handler: object) -> None:
        self.route_pattern = pattern
        self.route_handler = handler

    async def set_content(self, html: str, wait_until: str, timeout: int) -> None:
        self.html = html
        self.wait_until = wait_until
        self.timeout = timeout

    async def evaluate(self, expression: str, arg: object = None) -> object:
        return None

    async def screenshot(self, **kwargs: object) -> bytes:
        self.screenshot_after_wait = self.wait_finished
        return b"jpeg"

    async def content(self) -> str:
        return self.html

    async def close(self) -> None:
        self.closed = True


class FakeRenderBrowser:
    def __init__(self, page: FakeRenderPage) -> None:
        self.page = page

    async def new_page(self) -> FakeRenderPage:
        return self.page


class TestRenderToJpegAssetWait(unittest.IsolatedAsyncioTestCase):
    async def test_screenshot_waits_for_slide_images(self) -> None:
        page = FakeRenderPage()

        async def mark_wait_done(wait_page: FakeRenderPage) -> None:
            wait_page.wait_finished = True

        with patch("app.nodes.render_and_contrast.wait_for_slide_images", side_effect=mark_wait_done):
            slide, rendered, err = await _render_one(
                FakeRenderBrowser(page),  # type: ignore[arg-type]
                {"filename": "slide_01.html", "html": "<html><head></head><body>x</body></html>"},
                [],
            )

        self.assertIsNone(err)
        self.assertEqual(slide["filename"], "slide_01.html")
        self.assertEqual(rendered, {"filename": "slide_01.jpeg", "jpeg_bytes": b"jpeg"})
        self.assertTrue(page.screenshot_after_wait)
        self.assertTrue(page.closed)

    async def test_reports_error_when_asset_wait_reports_issue(self) -> None:
        page = FakeRenderPage()

        async def raise_wait_issue(wait_page: FakeRenderPage) -> None:
            wait_page.wait_finished = True
            raise RuntimeError("timed out waiting for image")

        with patch("app.nodes.render_and_contrast.wait_for_slide_images", side_effect=raise_wait_issue):
            slide, rendered, err = await _render_one(
                FakeRenderBrowser(page),  # type: ignore[arg-type]
                {"filename": "slide_01.html", "html": "<html><head></head><body>x</body></html>"},
                [],
            )

        self.assertEqual(slide["filename"], "slide_01.html")
        self.assertIsNone(rendered)
        self.assertIn("timed out waiting for image", err or "")
        self.assertFalse(page.screenshot_after_wait)
        self.assertTrue(page.closed)


if __name__ == "__main__":
    unittest.main()
