"""Parse LLM slide markers and validate HTML; drive retry routing."""

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


def parse_validate(state: AgentState) -> dict:
    logger.info("node=parse_validate job_id=%s", state.get("job_id"))
    raw = state.get("raw_slide_output") or ""
    parsed = _parse_slides(raw)
    valid: list[SlideItem] = [s for s in parsed if _valid_slide(s)]

    errors = list(state.get("errors") or [])
    retry_count = int(state.get("retry_count") or 0)

    if not valid:
        msg = "parse_validate: no valid slides after parsing markers"
        errors = errors + [msg]
        # Up to 3 generate_slides runs: increment 1→2→3 on failures, then stop.
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

    return {"slides_html": valid, "errors": errors}


def route_after_parse(state: AgentState) -> str:
    """Return 'retry' or 'continue' for conditional edges from parse_validate."""
    slides = state.get("slides_html") or []
    retry_count = int(state.get("retry_count") or 0)
    if slides:
        return "continue"
    # retry_count is incremented on each failed parse; retry until 3 attempts (rc 1,2,3).
    if retry_count < 3:
        return "retry"
    return "continue"
