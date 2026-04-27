"""Sanitization utilities for pipeline inputs and LLM outputs."""

from __future__ import annotations

import re

_SLIDE_MARKER_RE = re.compile(r"###SLIDE_FILE:[^\n]*", re.IGNORECASE)
_END_SLIDE_RE = re.compile(r"###END_SLIDE###", re.IGNORECASE)


def sanitize_brief_output(text: str) -> str:
    """Remove slide pipeline markers from the optimized brief (LLM 1 output).

    Prevents a compromised or manipulated brief from injecting delimiters that
    would be misinterpreted by the generate_slides node (LLM 2).
    """
    text = _SLIDE_MARKER_RE.sub("", text)
    text = _END_SLIDE_RE.sub("", text)
    return text
