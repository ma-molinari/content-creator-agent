"""POST job completion to Go API."""

import logging

import httpx

from app.config import get_settings
from app.state import AgentState

logger = logging.getLogger(__name__)


def _summarize_errors(errors: list[str]) -> str:
    if not errors:
        return "unknown worker error"
    return "; ".join(errors[:5])


def _build_assistant_text(state: AgentState) -> str:
    if state.get("assistant_text"):
        return str(state["assistant_text"])
    brief = (state.get("optimized_brief") or "").strip()
    if brief:
        return brief
    return "Conteúdo do carrossel foi gerado; veja as imagens anexas."


async def finalize(state: AgentState) -> dict:
    logger.info("node=finalize job_id=%s", state.get("job_id"))
    settings = get_settings()
    job_id = state.get("job_id") or ""
    errors = list(state.get("errors") or [])
    artifacts = state.get("artifacts") or []

    base = settings.go_api_url.rstrip("/")
    url = f"{base}/internal/jobs/{job_id}/complete"
    headers = {
        "Content-Type": "application/json",
        "X-Worker-API-Key": settings.worker_api_key,
    }

    no_artifacts = len(artifacts) == 0
    if no_artifacts and errors:
        body = {"error": _summarize_errors(errors)}
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, json=body, headers=headers)
            if r.status_code >= 400:
                errors.append(f"finalize callback failed: {r.status_code} {r.text}")
        return {"errors": errors}

    assistant = _build_assistant_text(state)
    payload = {
        "assistantText": assistant,
        "artifacts": [
            {"s3Key": a["s3_key"], "slideNumber": a["slide_number"]} for a in artifacts
        ],
        "error": None,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(url, json=payload, headers=headers)
        if r.status_code >= 400:
            errors.append(f"finalize callback failed: {r.status_code} {r.text}")

    return {"errors": errors}
