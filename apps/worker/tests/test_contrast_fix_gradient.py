"""Contrast fix: gradient backdrop must not mask low-contrast text (transparent bg + gradient)."""

from __future__ import annotations

import unittest

from playwright.async_api import async_playwright

from app.nodes.contrast_fix import _CONTRAST_FIX_JS

_CHROMIUM_LAUNCH_ARGS = [
    "--disable-background-networking",
    "--disable-extensions",
    "--no-default-browser-check",
]


def _minimal_slide_html(background_css: str, paragraph_color: str) -> str:
    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<style> html,body {{ margin:0; padding:0; }} </style></head><body style="width:1080px;height:1350px;margin:0;overflow:hidden;font-family:system-ui,sans-serif;{background_css}">
<p style="margin:48px;font-size:24px;font-weight:500;color:{paragraph_color};">Texto baixo contraste sobre gradiente</p>
</body></html>"""


class TestContrastFixGradient(unittest.IsolatedAsyncioTestCase):
    async def test_gray_on_dark_gradient_triggers_fixup(self) -> None:
        bg = (
            "background-color:transparent;"
            "background-image:linear-gradient(180deg, rgb(15, 23, 42) 0%, rgb(2, 6, 23) 100%);"
        )
        html = _minimal_slide_html(bg, "#475569")
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=_CHROMIUM_LAUNCH_ARGS)
            try:
                page = await browser.new_page()
                await page.set_viewport_size({"width": 1080, "height": 1350})
                await page.set_content(html, wait_until="domcontentloaded")
                await page.evaluate(_CONTRAST_FIX_JS)
                fixed = await page.content()
            finally:
                await browser.close()
        self.assertIn("__pipeline_contrast_fix", fixed)
        self.assertIn('data-cf="1"', fixed)
        self.assertIn("#e2e8f0", fixed)

    async def test_solid_white_bg_dark_body_text_unchanged(self) -> None:
        bg = "background-color:#ffffff;"
        html = _minimal_slide_html(bg, "#1e293b")
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=_CHROMIUM_LAUNCH_ARGS)
            try:
                page = await browser.new_page()
                await page.set_viewport_size({"width": 1080, "height": 1350})
                await page.set_content(html, wait_until="domcontentloaded")
                await page.evaluate(_CONTRAST_FIX_JS)
                fixed = await page.content()
            finally:
                await browser.close()
        self.assertNotIn("__pipeline_contrast_fix", fixed)
        self.assertNotIn("data-cf", fixed)


if __name__ == "__main__":
    unittest.main()
