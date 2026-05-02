"""Quality gate for optimized brief before slide generation."""

from __future__ import annotations

import logging
import re

from app.state import AgentState, copy_errors

logger = logging.getLogger(__name__)

_MIN_LEN = 100


def _brief_valid(brief: str) -> bool:
    b = (brief or "").strip()
    if len(b) < _MIN_LEN:
        return False
    return bool(re.search(r"^##\s+\S", b, re.MULTILINE))


def validate_brief(state: AgentState) -> dict:
    logger.info("node=validate_brief job_id=%s", state.get("job_id"))
    brief = (state.get("optimized_brief") or "").strip()
    errors = copy_errors(state)
    count = int(state.get("brief_retry_count") or 0)

    if _brief_valid(brief):
        return {"errors": errors}

    msg = (
        "validate_brief: brief inválido (muito curto ou sem seção markdown '## …'); "
        f"comprimento={len(brief)}"
    )
    errors = errors + [msg]
    if count < 2:
        return {"errors": errors, "brief_retry_count": count + 1}
    return {"errors": errors}


def route_after_validate_brief(state: AgentState) -> str:
    """Route from validate_brief: ok → generate_slides, retry → optimize_prompt, fail → finalize."""
    if _brief_valid((state.get("optimized_brief") or "").strip()):
        return "ok"
    c = int(state.get("brief_retry_count") or 0)
    if c < 2:
        return "retry"
    return "fail"
