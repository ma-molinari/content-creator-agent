"""Tests for slide HTML injection before JPEG export."""

import unittest

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

    def test_empty_passthrough(self) -> None:
        self.assertEqual(enhance_slide_html_for_render(""), "")


if __name__ == "__main__":
    unittest.main()
