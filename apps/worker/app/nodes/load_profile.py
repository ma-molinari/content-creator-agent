"""Concatenate audit + brand into profile_text."""

import logging

from app.state import AgentState

logger = logging.getLogger(__name__)


def load_profile(state: AgentState) -> dict:
    logger.info("node=load_profile job_id=%s", state.get("job_id"))
    audit = (state.get("audit_text") or "").strip()
    brand = (state.get("brand_text") or "").strip()
    profile_text = f"## AUDIT\n{audit}\n\n## BRAND\n{brand}"
    return {"profile_text": profile_text}
