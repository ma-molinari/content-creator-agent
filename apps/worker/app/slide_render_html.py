"""HTML tweaks for slide JPEG export (typography + font loading + layout safety)."""

from __future__ import annotations

import re

_HEAD_RE = re.compile(r"<head\b[^>]*>", re.IGNORECASE)
_BODY_END_RE = re.compile(r"</body\s*>", re.IGNORECASE)


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

_BODY_END_INJECTION = (
    '<style id="__pipeline_layout_safety">'
    # Previne o anti-padrão "título no topo + conteúdo no rodapé + centro vazio".
    # Sobrescreve space-between apenas no container direto de body (cascade posterior).
    # Containers internos (cards, listas) não são afetados pois não são filhos diretos de body.
    "body>div,body>main,body>section,body>article{"
    "justify-content:flex-start!important"
    "}"
    "</style>"
)


def enhance_slide_html_for_render(html: str) -> str:
    """Insert preconnect + typography in head and layout safety CSS before </body>."""
    if not (html or "").strip():
        return html
    m = _HEAD_RE.search(html)
    if m:
        html = html[: m.end()] + _SLIDE_HEAD_INJECTION + html[m.end() :]
    m2 = _BODY_END_RE.search(html)
    if m2:
        html = html[: m2.start()] + _BODY_END_INJECTION + html[m2.start() :]
    return html
