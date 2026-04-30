"""HTML tweaks for slide JPEG export (typography + font loading)."""

from __future__ import annotations

import re

_HEAD_RE = re.compile(r"<head\b[^>]*>", re.IGNORECASE)


# Injected early in <head>: preconnect speeds up Google Fonts; pipeline CSS improves rasterization.
_SLIDE_HEAD_INJECTION = (
    '<link rel="preconnect" href="https://fonts.googleapis.com"/>'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>'
    '<style id="__pipeline_slide_typography">'
    "html{-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;"
    "text-rendering:optimizeLegibility}"
    "body{font-optical-sizing:auto}"
    "</style>"
)


def enhance_slide_html_for_render(html: str) -> str:
    """Insert preconnect + global typography hints so Playwright export matches design intent."""
    if not (html or "").strip():
        return html
    m = _HEAD_RE.search(html)
    if m:
        end = m.end()
        return html[:end] + _SLIDE_HEAD_INJECTION + html[end:]
    return html
