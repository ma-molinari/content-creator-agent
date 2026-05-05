"""Compute max output tokens for generate_slides from target slide count."""

from __future__ import annotations

from typing import Protocol


class _TokenSettings(Protocol):
    """Structural type: matches ``Settings`` fields used below (no import cycle)."""

    generate_slides_max_tokens: int | None
    generate_slides_tokens_base: int
    generate_slides_tokens_per_slide: int
    generate_slides_max_tokens_cap: int


# Default N when the user does not request a specific count (rough mid of 6–10).
_DEFAULT_SLIDE_BUDGET = 8

# Extra headroom added to max_tokens on parse/design retries (capped by settings).
MAX_TOKENS_RETRY_HINT = 800


def compute_max_output_tokens(
    requested_slide_count: int | None,
    settings: _TokenSettings,
) -> int:
    if settings.generate_slides_max_tokens is not None:
        out = settings.generate_slides_max_tokens
    else:
        n = requested_slide_count if requested_slide_count is not None else _DEFAULT_SLIDE_BUDGET
        n = max(1, min(n, 20))
        out = settings.generate_slides_tokens_base + n * settings.generate_slides_tokens_per_slide
    return min(out, settings.generate_slides_max_tokens_cap)
