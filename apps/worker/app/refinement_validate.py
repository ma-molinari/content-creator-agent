"""Refinement guards: compare visible copy between HTML versions (visual-only scope)."""

from __future__ import annotations

from bs4 import BeautifulSoup

from app.state import SlideItem

_VISUAL_ONLY_ERROR = (
    "texto visível não coincide com o slide anterior; reverta o texto ao original e altere apenas "
    "CSS/cores/layout não-textual conforme a instrução."
)


def visible_text_normalized(html: str) -> str:
    """Extract visible text, normalize whitespace for stable comparison."""
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines: list[str] = []
    for line in text.splitlines():
        chunk = " ".join(line.split())
        if chunk:
            lines.append(chunk)
    return "\n".join(lines)


def visual_copy_preserved(existing_by_file: dict[str, str], parsed: list[SlideItem]) -> tuple[bool, list[str]]:
    """Return (ok, error_lines) — one error per slide with divergent visible text (case-insensitive filename keys)."""
    errors: list[str] = []
    for item in parsed:
        raw_name = (item.get("filename") or "").strip() or "slide.html"
        key = raw_name.lower()
        old_html = existing_by_file.get(key)
        if old_html is None:
            continue
        old_t = visible_text_normalized(old_html)
        new_t = visible_text_normalized(item.get("html") or "")
        if old_t != new_t:
            errors.append(f"copy_preservation: {raw_name}: {_VISUAL_ONLY_ERROR}")
    return (len(errors) == 0, errors)


def existing_slides_index(slides: list[SlideItem] | None) -> dict[str, str]:
    """Map lowercased filename -> html."""
    out: dict[str, str] = {}
    for s in slides or []:
        fn = (s.get("filename") or "").strip()
        if not fn:
            continue
        out[fn.lower()] = s.get("html") or ""
    return out
