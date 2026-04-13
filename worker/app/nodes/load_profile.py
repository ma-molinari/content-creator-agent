"""Concatenate audit + brand into profile_text."""

from app.state import AgentState


def load_profile(state: AgentState) -> dict:
    audit = (state.get("audit_text") or "").strip()
    brand = (state.get("brand_text") or "").strip()
    profile_text = f"## AUDIT\n{audit}\n\n## BRAND\n{brand}"
    return {"profile_text": profile_text}
