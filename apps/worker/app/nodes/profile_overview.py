"""Build profile overview and append cached visual reference summary."""

from __future__ import annotations

import logging
from typing import Any

from app.nodes.describe_references import describe_references
from app.state import AgentState

logger = logging.getLogger(__name__)

_REFERENCE_SUMMARY_CACHE: dict[tuple[str, ...], str] = {}


async def profile_overview(state: AgentState) -> dict[str, object]:
    logger.info("node=profile_overview job_id=%s", state.get("job_id"))
    audit = (state.get("audit_text") or "").strip()
    brand = (state.get("brand_text") or "").strip()
    base = f"## AUDIT\n{audit}\n\n## BRAND\n{brand}"
    keys = tuple(state.get("reference_s3_keys") or [])
    out: dict[str, Any] = {
        "profile_text": base,
        "profile_overview": {
            "audit_text": audit,
            "brand_text": brand,
            "reference_s3_keys": list(keys),
            "visual_reference_summary": "",
            "cache_hit": False,
        },
    }
    if not keys:
        return out
    if keys in _REFERENCE_SUMMARY_CACHE:
        summary = _REFERENCE_SUMMARY_CACHE[keys]
        out["profile_text"] = f"{base}\n\n{summary}" if summary else base
        out["profile_overview"]["visual_reference_summary"] = summary
        out["profile_overview"]["cache_hit"] = True
        return out
    described = await describe_references({**state, "profile_text": base})  # type: ignore[arg-type]
    profile_text = str(described.get("profile_text") or base)
    summary = profile_text.replace(base, "", 1).strip()
    _REFERENCE_SUMMARY_CACHE[keys] = summary
    overview = dict(out["profile_overview"])
    overview["visual_reference_summary"] = summary
    if described.get("errors"):
        out["errors"] = described["errors"]
    out["profile_text"] = profile_text
    out["profile_overview"] = overview
    return out
