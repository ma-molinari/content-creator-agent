"""Reject abusive user prompt fields before any LLM node runs."""

import logging

from app.prompt_security import (
    REASON_PROFILE_MAX_LENGTH,
    USER_PROFILE_TEXT_TOO_LONG_MESSAGE,
    USER_PROMPT_REJECT_MESSAGE,
    validate_prompt_security_bundle,
)
from app.state import AgentState, copy_errors

logger = logging.getLogger(__name__)


def prompt_security_validate(state: AgentState) -> dict:
    logger.info("node=prompt_security_validate job_id=%s", state.get("job_id"))
    ok, rule = validate_prompt_security_bundle(state)
    if ok:
        return {}

    jid = state.get("job_id")
    logger.warning(
        "prompt_security_validate rejected job_id=%s rule=%s",
        jid,
        rule,
    )
    errors = copy_errors(state)
    if rule == REASON_PROFILE_MAX_LENGTH:
        errors.append(USER_PROFILE_TEXT_TOO_LONG_MESSAGE)
    else:
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
