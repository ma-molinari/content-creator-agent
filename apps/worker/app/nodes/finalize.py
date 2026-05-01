"""POST job completion to Go API."""

from __future__ import annotations

import asyncio
import logging

from app.api_client import post_complete_callback
from app.config import get_settings
from app.nodes.finalize_messages import (
    JOB_FAILURE_CALLBACK_TRANSPORT,
    JOB_FAILURE_GENERIC,
    JOB_FAILURE_INCOMPLETE_CAROUSEL,
)
from app.prompt_security import USER_PROMPT_REJECT_MESSAGE
from app.sanitize import sanitize_brief_output
from app.slide_artifact_cleanup import delete_slide_artifact_keys_sync
from app.state import AgentState, ArtifactRef

logger = logging.getLogger(__name__)


def _compute_expected_delivery(state: AgentState) -> int:
    """Slides we expect persisted when render + upload behave correctly."""
    rendered = state.get("rendered_slides") or []
    n_rendered = len(rendered)
    req = state.get("requested_slide_count")
    requested_n = int(req) if isinstance(req, int) else None

    if requested_n is None:
        return n_rendered

    if n_rendered == 0:
        return requested_n

    # Discrepancy between negotiated count and actual renders → require the cautious maximum.
    return max(n_rendered, requested_n)


def _failure_message_for_callback(errors: list[str], *, mismatch_delivery: bool) -> str:
    if any(e == USER_PROMPT_REJECT_MESSAGE for e in errors):
        return USER_PROMPT_REJECT_MESSAGE
    if mismatch_delivery:
        return JOB_FAILURE_INCOMPLETE_CAROUSEL
    return JOB_FAILURE_GENERIC


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
    artifacts: list[ArtifactRef] = list(state.get("artifacts") or [])
    expected = _compute_expected_delivery(state)
    mismatch = expected > 0 and len(artifacts) != expected
    failure_no_output = len(artifacts) == 0 and bool(errors)
    send_failure_payload = mismatch or failure_no_output

    base = settings.go_api_url.rstrip("/")
    url = f"{base}/internal/jobs/{job_id}/complete"
    headers = {
        "Content-Type": "application/json",
        "X-Worker-API-Key": settings.worker_api_key,
    }

    if send_failure_payload:
        removal_keys = [a["s3_key"] for a in artifacts if (a.get("s3_key") or "").strip()]
        if mismatch and removal_keys:
            try:
                await asyncio.to_thread(
                    delete_slide_artifact_keys_sync,
                    settings,
                    removal_keys,
                )
            except Exception as exc:
                logger.error("finalize: slide cleanup failed job_id=%s err=%s", job_id, exc)

        api_error = _failure_message_for_callback(errors, mismatch_delivery=mismatch)
        body = {"error": api_error}
        try:
            r = await post_complete_callback(url, json_body=body, headers=headers, timeout=15.0)
            if r.status_code >= 400:
                errors.append(f"finalize callback failed: {r.status_code} {r.text}")
                try:
                    await post_complete_callback(
                        url,
                        json_body={"error": JOB_FAILURE_CALLBACK_TRANSPORT},
                        headers=headers,
                        timeout=10.0,
                    )
                except Exception as retry_exc:
                    logger.error("failed to send error callback: %s", retry_exc)
        except Exception as exc:
            logger.error("finalize callback error: %s", exc)
            errors.append(f"finalize callback error: {exc}")
            try:
                await post_complete_callback(
                    url,
                    json_body={"error": JOB_FAILURE_CALLBACK_TRANSPORT},
                    headers=headers,
                    timeout=10.0,
                )
            except Exception as retry_exc:
                logger.error("failed to send error callback: %s", retry_exc)
        return {"errors": errors, "artifacts": []}

    assistant = _build_assistant_text(state)
    payload = {
        "assistantText": assistant,
        "artifacts": [
            {"s3Key": a["s3_key"], "slideNumber": a["slide_number"]} for a in artifacts
        ],
        "error": None,
    }

    try:
        r = await post_complete_callback(url, json_body=payload, headers=headers, timeout=15.0)
        if r.status_code >= 400:
            errors.append(f"finalize callback failed: {r.status_code} {r.text}")
            try:
                await post_complete_callback(
                    url,
                    json_body={"error": JOB_FAILURE_CALLBACK_TRANSPORT},
                    headers=headers,
                    timeout=10.0,
                )
            except Exception as retry_exc:
                logger.error("failed to send error callback: %s", retry_exc)
    except Exception as exc:
        logger.error("finalize callback error: %s", exc)
        errors.append(f"finalize callback error: {exc}")
        try:
            await post_complete_callback(
                url,
                json_body={"error": JOB_FAILURE_CALLBACK_TRANSPORT},
                headers=headers,
                timeout=10.0,
            )
        except Exception as retry_exc:
            logger.error("failed to send error callback: %s", retry_exc)

    return {"errors": errors}
