"""Infer target slide count from the user message (pt-BR / en)."""

from __future__ import annotations

import re

# Reasonable bound for Instagram carousels; avoids matching years or large numbers.
_MAX_SLIDES = 20
_MIN_SLIDES = 1

_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    # "carrossel de 6", "carousel of 5"
    (re.compile(r"carrossel\s+(?:de|com)\s*(\d{1,2})\b", re.IGNORECASE), 1),
    (re.compile(r"carousel\s+(?:of|with)\s*(\d{1,2})\b", re.IGNORECASE), 1),
    # "6 slides", "6 slide"
    (re.compile(r"\b(\d{1,2})\s+slides?\b", re.IGNORECASE), 1),
    # "com 6 slides", "with 5 slides"
    (re.compile(r"(?:^|\W)(?:com|with)\s*(\d{1,2})\s+slides?\b", re.IGNORECASE), 1),
]


def infer_requested_slide_count(text: str) -> int | None:
    """
    If the user explicitly asks for N slides, return N; otherwise None.
    Intentional ambiguity (e.g. two different N in one message) returns None.
    """
    if not (text or "").strip():
        return None

    found: set[int] = set()
    for pat, group in _PATTERNS:
        for m in pat.finditer(text):
            try:
                n = int(m.group(group))
            except (TypeError, ValueError):
                continue
            if _MIN_SLIDES <= n <= _MAX_SLIDES:
                found.add(n)

    if len(found) == 1:
        return found.pop()
    return None
