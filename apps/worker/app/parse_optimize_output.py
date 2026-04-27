"""Parse dual-region output from the optimize_prompt LLM call."""

from __future__ import annotations

import re

_BRIEF_TAG = re.compile(
    r"<brief_para_gerador>\s*(.*?)\s*</brief_para_gerador>",
    re.DOTALL | re.IGNORECASE,
)
_MSG_TAG = re.compile(
    r"<mensagem_usuario>\s*(.*?)\s*</mensagem_usuario>",
    re.DOTALL | re.IGNORECASE,
)


def _strip_optional_outer_fence(text: str) -> str:
    """Remove a single leading/trailing Markdown code fence, if the whole string is wrapped."""
    t = text.strip()
    if not t.startswith("```"):
        return t
    first_nl = t.find("\n")
    if first_nl == -1:
        return t
    rest = t[first_nl + 1 :]
    if rest.rstrip().endswith("```"):
        inner = rest.rstrip()[:-3]
        return inner.strip()
    return t


def split_optimize_response(raw: str) -> tuple[str, str | None]:
    """Split LLM output into generator brief and optional user-facing message.

    Returns:
        (optimized_brief, assistant_text)
        - optimized_brief: content of ``<brief_para_gerador>`` if present and non-empty;
          otherwise the full ``raw`` (backward compatible when tags are missing).
        - assistant_text: content of ``<mensagem_usuario>`` if present and non-empty; else None.
    """
    cleaned = _strip_optional_outer_fence(raw)
    brief_m = _BRIEF_TAG.search(cleaned)
    msg_m = _MSG_TAG.search(cleaned)

    if brief_m:
        brief = brief_m.group(1).strip()
        if not brief:
            # Empty generator tag: keep full model output (compat / mis-generation).
            brief = raw.strip()
    else:
        # No tag: old behaviour — entire output is the brief.
        brief = cleaned.strip() if cleaned.strip() else raw.strip()

    user_msg: str | None = None
    if msg_m:
        inner = msg_m.group(1).strip()
        inner = _strip_optional_outer_fence(inner)
        if inner:
            user_msg = inner

    return (brief, user_msg)
