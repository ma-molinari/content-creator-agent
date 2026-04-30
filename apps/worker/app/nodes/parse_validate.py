"""Parse LLM slide markers and validate HTML; drive retry routing."""

from __future__ import annotations

import logging
import re

from app.state import AgentState, SlideItem

logger = logging.getLogger(__name__)

_SLIDE_BLOCK = re.compile(
    r"###SLIDE_FILE:\s*([^\s#]+?)\s*###\s*(.*?)\s*###END_SLIDE###",
    re.DOTALL | re.IGNORECASE,
)

_MIN_HTML_LEN = 80


def _parse_slides(raw: str) -> list[SlideItem]:
    items: list[SlideItem] = []
    for m in _SLIDE_BLOCK.finditer(raw or ""):
        filename = (m.group(1) or "").strip()
        html = (m.group(2) or "").strip()
        if not filename.lower().endswith(".html"):
            filename = f"{filename}.html" if filename else "slide.html"
        items.append({"filename": filename, "html": html})
    return items


def _valid_slide(item: SlideItem) -> bool:
    html = item.get("html") or ""
    if len(html) < _MIN_HTML_LEN:
        return False
    lower = html.lower()
    return "<html" in lower and "</html>" in lower


def _expected_filenames(n: int) -> list[str]:
    return [f"slide_{i:02d}.html" for i in range(1, n + 1)]


def _structured_parse_messages(
    state: AgentState,
    parsed: list[SlideItem],
    valid: list[SlideItem],
    got_valid: int,
) -> list[str]:
    """Human- and LLM-oriented diagnostics for generate_slides retries."""
    msgs: list[str] = []
    valid_names = {s.get("filename") or "" for s in valid}
    malformed = [s.get("filename") or "slide.html" for s in parsed if not _valid_slide(s)]

    requested = state.get("requested_slide_count")
    if isinstance(requested, int):
        expected = set(_expected_filenames(requested))
        missing = sorted(expected - valid_names)
        msgs.append(
            f"parse_validate: esperados {requested} slides válidos; recebidos {got_valid}."
        )
        if missing:
            msgs.append(
                "parse_validate: arquivos ausentes (gere cada bloco completo nesta tentativa): "
                + ", ".join(missing)
            )
    else:
        msgs.append(f"parse_validate: slides válidos após parsing: {got_valid}.")

    if malformed:
        msgs.append(
            "parse_validate: HTML inválido ou truncado (cada slide precisa de documento completo "
            "com <html> e </html>): "
            + ", ".join(malformed)
        )

    return msgs


def _requested_count_mismatch(
    state: AgentState, valid: list[SlideItem]
) -> tuple[bool, int | None, int]:
    """Returns (mismatch, requested_or_none, got_count)."""
    requested = state.get("requested_slide_count")
    if not isinstance(requested, int):
        return (False, None, len(valid))
    if len(valid) != requested:
        return (True, requested, len(valid))
    return (False, requested, len(valid))


def _failure_return(
    errors: list[str],
    retry_count: int,
    diag: list[str],
) -> dict:
    errors = errors + diag
    if retry_count < 3:
        return {
            "slides_html": [],
            "errors": errors,
            "retry_count": retry_count + 1,
        }
    return {
        "slides_html": [],
        "errors": errors,
    }


def parse_validate(state: AgentState) -> dict:
    logger.info("node=parse_validate job_id=%s", state.get("job_id"))
    raw = state.get("raw_slide_output") or ""
    parsed = _parse_slides(raw)
    valid: list[SlideItem] = [s for s in parsed if _valid_slide(s)]

    errors = list(state.get("errors") or [])
    retry_count = int(state.get("retry_count") or 0)

    mismatch, req_n, got = _requested_count_mismatch(state, valid)
    diag = _structured_parse_messages(state, parsed, valid, got)

    if mismatch:
        head = f"parse_validate: expected {req_n} slides, got {got} valid"
        logger.info("node=parse_validate job_id=%s %s", state.get("job_id"), head)
        return _failure_return(errors, retry_count, [head] + diag)

    if not valid:
        head = "parse_validate: no valid slides after parsing markers"
        return _failure_return(errors, retry_count, [head] + diag)

    return {"slides_html": valid, "errors": errors}


def route_after_parse(state: AgentState) -> str:
    """Return 'retry', 'continue', or 'fail' for conditional edges from parse_validate."""
    slides = state.get("slides_html") or []
    if slides:
        return "continue"
    if int(state.get("retry_count") or 0) < 3:
        return "retry"
    return "fail"
