"""Static HTML/CSS design checks for carousel slides (Phase 1 — no browser).

Aligned with the structured slide-generation contract: no JS, no remote raster/CDN assets,
Google Fonts only as external CSS, Plus Jakarta Sans default unless another GF family
is clearly loaded and used, and viewport dimensions 1080×1350.

This module implements a **verifiable subset** of that prompt; it complements
human-facing guidance in ``.cursor/rules/design/`` (UI image designer,
UX architect for carousel) which are not executable.

Heuristics may produce false positives/negatives (e.g. uncommon ``font-family``
syntax or unconventional layout sizing); document changes here when tightening rules.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup

from app.s3_image_utils import is_allowed_s3_url

_ALLOWED_FONT_NETLOCS = frozenset({"fonts.googleapis.com", "fonts.gstatic.com"})

_DEFAULT_FONT_FAMILY = "plus jakarta sans"
# Fonts that are no longer accepted as default or as alternate (legacy pipeline fonts).
_BLOCKED_LEGACY_FONTS = frozenset({"inter"})
_HEX_COLOR = re.compile(r"#([0-9a-fA-F]{6})\b")

_SCRIPT_TAG = re.compile(r"<\s*script\b", re.I)
_INLINE_HANDLER = re.compile(r"\bon[a-z][a-z0-9_]*\s*=", re.I)

_CSS_URL = re.compile(
    r"""url\(\s*(['"]?)(https?://[^'")\s]+)\1\s*\)""",
    re.I,
)
_CSS_IMPORT = re.compile(
    r"""@import\s+(?:url\s*\(\s*)?(['"]?)(https?://[^'")\s]+)\1""",
    re.I,
)

_HTTP_URL = re.compile(r"https?://[^\s\"')]+", re.I)


def _netloc(url: str) -> str:
    try:
        return (urlparse(url).netloc or "").lower()
    except ValueError:
        return ""


def _allowed_remote_netloc(url: str) -> bool:
    host = _netloc(url)
    return (
        host in _ALLOWED_FONT_NETLOCS
        or host.endswith(".fonts.gstatic.com")
        or is_allowed_s3_url(url)
    )


def _extract_css_blob(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    parts: list[str] = []
    for tag in soup.find_all("style"):
        if tag.string:
            parts.append(tag.string)
    for tag in soup.find_all(True):
        style = tag.get("style")
        if style:
            parts.append(str(style))
    return "\n".join(parts)


def _collect_style_http_urls(css_blob: str) -> list[str]:
    found: list[str] = []
    for rx in (_CSS_URL, _CSS_IMPORT):
        for m in rx.finditer(css_blob):
            found.append(m.group(2))
    return found


def _google_font_family_names(url: str) -> list[str]:
    if "fonts.googleapis.com" not in url.lower():
        return []
    q = urlparse(url).query
    names: list[str] = []
    for raw in parse_qs(q).get("family", []):
        decoded = unquote(raw.replace("+", " "))
        base = re.split(r"[:@,]", decoded, maxsplit=1)[0].strip()
        if base:
            names.append(base.lower())
    return names


def _imports_default_font_from_googleapis(urls: list[str]) -> bool:
    for u in urls:
        if "fonts.googleapis.com" not in u.lower():
            continue
        if any(n == _DEFAULT_FONT_FAMILY for n in _google_font_family_names(u)):
            return True
        u_lower = u.lower()
        if "plus+jakarta+sans" in u_lower or "plus%20jakarta%20sans" in u_lower:
            return True
    return False


def _font_family_blocks(html: str, css_blob: str) -> str:
    return f"{html}\n{css_blob}"


def _mentions_default_font_in_font_family(html: str, css_blob: str) -> bool:
    return _mentions_family_name(html, css_blob, _DEFAULT_FONT_FAMILY)


def _mentions_family_name(html: str, css_blob: str, family_lower: str) -> bool:
    """True if ``family_lower`` appears inside a ``font-family`` declaration."""
    blob = _font_family_blocks(html, css_blob).lower()
    target = family_lower.strip().lower()
    compact_target = target.replace(" ", "")
    for m in re.finditer(r"font-family\s*:\s*([^;{}]+)", blob, re.I):
        decl = re.sub(r'["\']', "", m.group(1).lower())
        decl_compact = decl.replace(" ", "")
        if target in decl:
            return True
        if compact_target and compact_target in decl_compact:
            return True
    return False


def check_no_javascript(html: str) -> list[str]:
    if _SCRIPT_TAG.search(html or ""):
        return ["uso de <script> é proibido (slides sem JS)"]
    if _INLINE_HANDLER.search(html or ""):
        return ["handlers inline (on*) são proibidos (slides sem JS)"]
    return []


def check_remote_assets(html: str) -> list[str]:
    errs: list[str] = []
    soup = BeautifulSoup(html or "", "html.parser")
    css_blob = _extract_css_blob(html)

    for tag_name, attr in (
        ("img", "src"),
        ("video", "src"),
        ("audio", "src"),
        ("iframe", "src"),
        ("embed", "src"),
        ("source", "src"),
    ):
        for node in soup.find_all(tag_name):
            val = node.get(attr)
            if not val or not isinstance(val, str):
                continue
            v = val.strip()
            if v.startswith(("http://", "https://")) and not _allowed_remote_netloc(v):
                errs.append(f"URL remota proibida em <{tag_name} {attr}>: {v[:120]}")

    for node in soup.find_all(True):
        for attr_name in ("srcset", "poster"):
            val = node.get(attr_name)
            if not val or not isinstance(val, str):
                continue
            for piece in val.split(","):
                url_part = piece.strip().split()[0] if piece.strip() else ""
                if url_part.startswith(("http://", "https://")) and not _allowed_remote_netloc(url_part):
                    errs.append(f"URL remota proibida em {attr_name}: {url_part[:120]}")

    for url in _collect_style_http_urls(css_blob):
        if url.startswith(("http://", "https://")) and not _allowed_remote_netloc(url):
            errs.append(f"url() remoto proibido no CSS: {url[:120]}")

    return errs


def check_external_stylesheets(html: str) -> list[str]:
    soup = BeautifulSoup(html or "", "html.parser")
    for link in soup.find_all("link"):
        href = link.get("href")
        if not href or not isinstance(href, str):
            continue
        h = href.strip()
        if not h.startswith(("http://", "https://")):
            continue
        if _allowed_remote_netloc(h):
            continue
        return [f"<link href> remoto permitido só para Google Fonts: {h[:120]}"]
    return []


def check_default_typography(html: str) -> list[str]:
    """Plus Jakarta Sans via Google Fonts + ``font-family``, or another GF family clearly imported and used."""
    css_blob = _extract_css_blob(html)
    text_blob = f"{html}\n{css_blob}"

    gf_urls = list(dict.fromkeys(_HTTP_URL.findall(text_blob)))
    gf_urls = [u for u in gf_urls if "fonts.googleapis.com" in u.lower()]

    default_import = _imports_default_font_from_googleapis(gf_urls)
    default_used = _mentions_default_font_in_font_family(html, css_blob)

    if default_import and default_used:
        return []

    alternate_ok = False
    for u in gf_urls:
        for fam in _google_font_family_names(u):
            if fam == _DEFAULT_FONT_FAMILY or fam in _BLOCKED_LEGACY_FONTS:
                continue
            if _mentions_family_name(html, css_blob, fam):
                alternate_ok = True
                break
        if alternate_ok:
            break

    if alternate_ok:
        return []

    return [
        "tipografia: importe Plus Jakarta Sans via fonts.googleapis.com e use "
        "'Plus Jakarta Sans' em font-family no body (ou outra família explicitamente carregada em GF e usada)"
    ]


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _colors_close(h1: str, h2: str, tolerance: int = 15) -> bool:
    r1, g1, b1 = _hex_to_rgb(h1)
    r2, g2, b2 = _hex_to_rgb(h2)
    return abs(r1 - r2) <= tolerance and abs(g1 - g2) <= tolerance and abs(b1 - b2) <= tolerance


def check_reference_colors(html: str, prescription_blob: str) -> list[str]:
    """Warn when none of the reference hex colors (from the prescription blob) appear in slide CSS."""
    if not prescription_blob:
        return []
    ref_hexes = [m.group(1).lower() for m in _HEX_COLOR.finditer(prescription_blob)]
    if len(ref_hexes) < 3:
        return []
    css_blob = _extract_css_blob(html)
    slide_hexes = [m.group(1).lower() for m in _HEX_COLOR.finditer(f"{html}\n{css_blob}")]
    for ref in ref_hexes:
        if any(_colors_close(ref, s) for s in slide_hexes):
            return []
    return [
        "referências visuais: nenhuma cor do resumo detectada no CSS do slide — verifique paleta"
    ]


def check_viewport_canvas(html: str) -> list[str]:
    """Require 1080px and 1350px somewhere in authored CSS (aligned to worker JPEG size)."""
    css_blob = _extract_css_blob(html)
    if not re.search(r"\b1080\s*px\b", css_blob, re.I):
        return ["viewport: largura 1080px no CSS do slide não encontrada"]
    if not re.search(r"\b1350\s*px\b", css_blob, re.I):
        return ["viewport: altura 1350px no CSS do slide não encontrada"]
    return []


def collect_design_violations(html: str, prescription_blob: str = "") -> list[str]:
    """Return human-readable violation messages (without ``validate_design:`` prefix)."""
    errs: list[str] = []
    errs.extend(check_no_javascript(html))
    errs.extend(check_remote_assets(html))
    errs.extend(check_external_stylesheets(html))
    errs.extend(check_default_typography(html))
    errs.extend(check_viewport_canvas(html))
    errs.extend(check_reference_colors(html, prescription_blob))
    return errs
