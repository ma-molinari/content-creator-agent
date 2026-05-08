"""Infer target slide count from the user message (pt-BR / en)."""

from __future__ import annotations

import re

# Reasonable bound for Instagram carousels; avoids matching years or large numbers.
_MAX_SLIDES = 20
_MIN_SLIDES = 1

_NUMBER_WORDS_PT = {
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "três": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
}

_NUMBER_WORDS_EN = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
}

_NUMBER_WORDS = {**_NUMBER_WORDS_PT, **_NUMBER_WORDS_EN}
_NUMBER_WORD_RE = "|".join(sorted(map(re.escape, _NUMBER_WORDS), key=len, reverse=True))

_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    # "carrossel de 6", "carousel of 5"
    (re.compile(r"(?:carrossel|carrousel)\s+(?:de|com)\s*(\d{1,2})\b", re.IGNORECASE), 1),
    (re.compile(r"carousel\s+(?:of|with)\s*(\d{1,2})\b", re.IGNORECASE), 1),
    # "6 slides", "6 slide"
    (re.compile(r"\b(\d{1,2})\s+slides?\b", re.IGNORECASE), 1),
    # "com 6 slides", "with 5 slides"
    (re.compile(r"(?:^|\W)(?:com|with)\s*(\d{1,2})\s+slides?\b", re.IGNORECASE), 1),
]

_WORD_PATTERNS: list[tuple[re.Pattern[str], int]] = [
    # "carrossel de dois slides", "carrousel com duas imagens"
    (re.compile(rf"\b(?:carrossel|carrousel|carousel)\s+(?:de|com|of|with)\s*({_NUMBER_WORD_RE})\b", re.IGNORECASE), 1),
    # "dois slides", "two slides"
    (re.compile(rf"\b({_NUMBER_WORD_RE})\s+slides?\b", re.IGNORECASE), 1),
]


def _coerce_slide_count(value: str) -> int | None:
    raw = (value or "").strip().lower()
    if not raw:
        return None
    if raw.isdigit():
        n = int(raw)
    else:
        n = _NUMBER_WORDS.get(raw)
        if n is None:
            return None
    if _MIN_SLIDES <= n <= _MAX_SLIDES:
        return n
    return None


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
            n = _coerce_slide_count(m.group(group))
            if n is None:
                continue
            found.add(n)

    for pat, group in _WORD_PATTERNS:
        for m in pat.finditer(text):
            n = _coerce_slide_count(m.group(group))
            if n is None:
                continue
            found.add(n)

    if len(found) == 1:
        return found.pop()
    return None
