"""WCAG contrast helpers (pure Python, no browser)."""

from __future__ import annotations

import re

_RGB_RE = re.compile(
    r"rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*([0-9.]+)\s*)?\)",
    re.IGNORECASE,
)


def relative_luminance(r: int, g: int, b: int) -> float:
    """WCAG 2.1 relative luminance for sRGB channels in 0..255."""
    def channel_linear(u: float) -> float:
        c = u / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    rs = channel_linear(float(r))
    gs = channel_linear(float(g))
    bs = channel_linear(float(b))
    return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs


def contrast_ratio(l1: float, l2: float) -> float:
    """Contrast ratio between two relative luminances (order-independent)."""
    hi = max(l1, l2)
    lo = min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def parse_rgb_string(css: str) -> tuple[int, int, int] | None:
    """Parse rgb()/rgba() string; returns None if unusable (invalid or too transparent)."""
    if not css or css.strip().lower() == "transparent":
        return None
    m = _RGB_RE.match(css.strip())
    if not m:
        return None
    r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
    alpha_s = m.group(4)
    if alpha_s is not None:
        try:
            a = float(alpha_s)
        except ValueError:
            return None
        if a < 0.99:
            return None
    return (r, g, b)


def wcag_threshold(font_size_px: float, is_bold: bool) -> float:
    """Minimum contrast ratio: 3.0 large/bold-large, else 4.5."""
    if font_size_px >= 24.0:
        return 3.0
    if is_bold and font_size_px >= 18.67:
        return 3.0
    return 4.5


def corrected_text_color(bg_luminance: float) -> str:
    """Pick accessible text hex for pipeline override; bg is background luminance 0..1."""
    if bg_luminance < 0.5:
        return "#e2e8f0"
    return "#1e293b"
