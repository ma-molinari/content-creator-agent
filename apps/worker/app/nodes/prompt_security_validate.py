"""Reject abusive user prompt fields before any LLM node runs."""

import logging

from app.prompt_security import USER_PROMPT_REJECT_MESSAGE, validate_user_prompt
from app.state import AgentState

logger = logging.getLogger(__name__)


def prompt_security_validate(state: AgentState) -> dict:
    logger.info("node=prompt_security_validate job_id=%s", state.get("job_id"))
    ok, rule = validate_user_prompt(state)
    if ok:
        return {}

    jid = state.get("job_id")
    logger.warning(
        "prompt_security_validate rejected job_id=%s rule=%s",
        jid,
        rule,
    )
    errors = list(state.get("errors") or [])
    errors.append(USER_PROMPT_REJECT_MESSAGE)
    return {
        "errors": errors,
        "prompt_validation_failed": True,
        "prompt_security_rule": rule or "",
    }


def route_after_prompt_security(state: AgentState) -> str:
    if state.get("prompt_validation_failed"):
        return "rejected"
    return "ok"
