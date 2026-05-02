"""Unit tests for WCAG contrast helpers."""

from __future__ import annotations

import unittest

from app.contrast_utils import (
    contrast_ratio,
    corrected_text_color,
    parse_rgb_string,
    relative_luminance,
    wcag_threshold,
)


class TestContrastUtils(unittest.TestCase):
    def test_relative_luminance_white_black_mid(self) -> None:
        self.assertAlmostEqual(relative_luminance(255, 255, 255), 1.0, places=5)
        self.assertAlmostEqual(relative_luminance(0, 0, 0), 0.0, places=5)
        mid = relative_luminance(128, 128, 128)
        self.assertGreater(mid, 0.1)
        self.assertLess(mid, 0.5)

    def test_contrast_ratio_known_pairs(self) -> None:
        lw = relative_luminance(255, 255, 255)
        lb = relative_luminance(0, 0, 0)
        self.assertAlmostEqual(contrast_ratio(lw, lb), 21.0, places=4)
        # ~#767676 on white ≈ 4.54:1 (WCAG boundary gray)
        lg = relative_luminance(118, 118, 118)
        self.assertGreater(contrast_ratio(lw, lg), 4.5)
        self.assertLess(contrast_ratio(lw, lg), 4.6)

    def test_parse_rgb_string(self) -> None:
        self.assertEqual(parse_rgb_string("rgb(10, 20, 30)"), (10, 20, 30))
        self.assertEqual(parse_rgb_string("  RGB(0, 0, 255) "), (0, 0, 255))
        self.assertEqual(parse_rgb_string("rgba(100, 50, 25, 1)"), (100, 50, 25))
        self.assertIsNone(parse_rgb_string("rgba(100, 50, 25, 0.5)"))
        self.assertIsNone(parse_rgb_string("transparent"))
        self.assertIsNone(parse_rgb_string("not a color"))

    def test_wcag_threshold(self) -> None:
        self.assertEqual(wcag_threshold(16.0, False), 4.5)
        self.assertEqual(wcag_threshold(24.0, False), 3.0)
        self.assertEqual(wcag_threshold(18.0, True), 4.5)
        self.assertEqual(wcag_threshold(18.67, True), 3.0)

    def test_corrected_text_color(self) -> None:
        self.assertEqual(corrected_text_color(0.1), "#e2e8f0")
        self.assertEqual(corrected_text_color(0.8), "#1e293b")


if __name__ == "__main__":
    unittest.main()
