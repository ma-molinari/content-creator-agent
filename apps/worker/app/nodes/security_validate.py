"""Structured security validation for user-controlled prompt fields."""

from __future__ import annotations

import logging

from app.prompt_security import (
    REASON_PROFILE_MAX_LENGTH,
    USER_PROFILE_TEXT_TOO_LONG_MESSAGE,
    USER_PROMPT_REJECT_MESSAGE,
    validate_prompt_security_bundle,
)
from app.state import AgentState, copy_errors

logger = logging.getLogger(__name__)


def security_validate(state: AgentState) -> dict[str, object]:
    logger.info("node=security_validate job_id=%s", state.get("job_id"))
    profile_text = f"## AUDIT\n{state.get('audit_text') or ''}\n\n## BRAND\n{state.get('brand_text') or ''}"
    check_state = dict(state)
    check_state["profile_text"] = profile_text
    ok, reason = validate_prompt_security_bundle(check_state)  # type: ignore[arg-type]
    if ok:
        return {
            "profile_text": profile_text,
            "security_result": {"ok": True},
        }
    errors = copy_errors(state)
    errors.append(
        USER_PROFILE_TEXT_TOO_LONG_MESSAGE
        if reason == REASON_PROFILE_MAX_LENGTH
        else USER_PROMPT_REJECT_MESSAGE
    )
    return {
        "profile_text": profile_text,
        "security_result": {
            "ok": False,
            "reason": reason or "unknown",
            "blocked_fields": ["profile_text"] if reason == REASON_PROFILE_MAX_LENGTH else ["raw_message"],
        },
        "prompt_validation_failed": True,
        "prompt_security_rule": reason or "",
        "errors": errors,
    }


def route_after_security(state: AgentState) -> str:
    result = state.get("security_result") or {}
    return "ok" if result.get("ok", False) else "rejected"
