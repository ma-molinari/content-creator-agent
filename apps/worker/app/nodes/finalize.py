"""POST job completion to Go API."""

import logging

from app.api_client import post_complete_callback
from app.config import get_settings
from app.sanitize import sanitize_brief_output
from app.state import AgentState

logger = logging.getLogger(__name__)


def _summarize_errors(errors: list[str]) -> str:
    if not errors:
        return "unknown worker error"
    return "; ".join(errors[:5])


def _build_assistant_text(state: AgentState) -> str:
    if state.get("assistant_text"):
        return sanitize_brief_output(str(state["assistant_text"]).strip())
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
        r = await post_complete_callback(url, json_body=body, headers=headers)
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

    r = await post_complete_callback(url, json_body=payload, headers=headers)
    if r.status_code >= 400:
        errors.append(f"finalize callback failed: {r.status_code} {r.text}")
        # Prevent the job from being stuck in processing by sending an error callback.
        await post_complete_callback(
            url,
            json_body={"error": "callback delivery failed"},
            headers=headers,
            timeout=10.0,
        )

    return {"errors": errors}
