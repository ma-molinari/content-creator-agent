"""POST job completion to Go API."""

from __future__ import annotations

import asyncio
import logging
from typing import Mapping

from app.api_client import post_complete_callback
from app.config import get_settings
from app.nodes.finalize_messages import (
    JOB_FAILURE_CALLBACK_TRANSPORT,
    JOB_FAILURE_GENERIC,
    JOB_FAILURE_HTML_ARTIFACT,
    JOB_FAILURE_INCOMPLETE_CAROUSEL,
    JOB_FAILURE_REFINEMENT_CONTEXT,
)
from app.prompt_security import USER_PROFILE_TEXT_TOO_LONG_MESSAGE, USER_PROMPT_REJECT_MESSAGE
from app.sanitize import sanitize_brief_output
from app.slide_artifact_cleanup import delete_slide_artifact_keys_sync
from app.state import AgentState, ArtifactRef, copy_errors

logger = logging.getLogger(__name__)

# Avoid echoing full API error bodies into worker state / logs surfaced downstream.
_CALLBACK_ERROR_SNIPPET_MAX = 384
_HTTP_ERROR_LOG_BODY_MAX = 2048

_FALLBACK_BODY: Mapping[str, str] = {"error": JOB_FAILURE_CALLBACK_TRANSPORT}


def _snippet_for_errors(text: str, *, max_len: int) -> str:
    t = (text or "").replace("\n", " ").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 3] + "..."


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


def _artifacts_missing_required_html_keys(artifacts: list[ArtifactRef]) -> bool:
    if not artifacts:
        return False
    return any(not str(a.get("html_s3_key") or "").strip() for a in artifacts)


def _failure_message_for_callback(
    errors: list[str],
    *,
    mismatch_delivery: bool,
    html_artifact_delivery_failed: bool,
) -> str:
    if any(e == USER_PROFILE_TEXT_TOO_LONG_MESSAGE for e in errors):
        return USER_PROFILE_TEXT_TOO_LONG_MESSAGE
    if any(e == USER_PROMPT_REJECT_MESSAGE for e in errors):
        return USER_PROMPT_REJECT_MESSAGE
    if any(e == JOB_FAILURE_REFINEMENT_CONTEXT for e in errors):
        return JOB_FAILURE_REFINEMENT_CONTEXT
    if mismatch_delivery:
        return JOB_FAILURE_INCOMPLETE_CAROUSEL
    if html_artifact_delivery_failed:
        return JOB_FAILURE_HTML_ARTIFACT
    return JOB_FAILURE_GENERIC


def _build_assistant_text(state: AgentState) -> str:
    if state.get("assistant_text"):
        return sanitize_brief_output(str(state["assistant_text"]).strip())
    brief = (state.get("optimized_brief") or "").strip()
    if brief:
        return brief
    return "Conteúdo do carrossel foi gerado; veja as imagens anexas."


async def _post_complete_with_transport_fallback(
    *,
    url: str,
    headers: dict[str, str],
    json_body: dict[str, object] | Mapping[str, str] | None,
    errors: list[str],
    timeout: float,
    fallback_timeout: float,
) -> None:
    try:
        r = await post_complete_callback(url, json_body=json_body, headers=headers, timeout=timeout)
        if r.status_code >= 400:
            raw_body = r.text or ""
            body_snip = _snippet_for_errors(raw_body, max_len=_CALLBACK_ERROR_SNIPPET_MAX)
            log_body_snip = _snippet_for_errors(raw_body, max_len=_HTTP_ERROR_LOG_BODY_MAX)
            logger.warning(
                "finalize callback HTTP error status=%s body_snippet=%r",
                r.status_code,
                log_body_snip,
            )
            errors.append(f"finalize callback failed: {r.status_code} {body_snip}")
            try:
                await post_complete_callback(
                    url,
                    json_body=dict(_FALLBACK_BODY),
                    headers=headers,
                    timeout=fallback_timeout,
                )
            except Exception as retry_exc:
                logger.error("failed to send error callback: %s", retry_exc)
    except Exception as exc:
        logger.error("finalize callback error: %s", exc)
        errors.append(f"finalize callback error: {exc}")
        try:
            await post_complete_callback(
                url,
                json_body=dict(_FALLBACK_BODY),
                headers=headers,
                timeout=fallback_timeout,
            )
        except Exception as retry_exc:
            logger.error("failed to send error callback: %s", retry_exc)


async def finalize(state: AgentState) -> dict:
    logger.info("node=finalize job_id=%s", state.get("job_id"))
    settings = get_settings()
    job_id = state.get("job_id") or ""
    errors = copy_errors(state)
    artifacts: list[ArtifactRef] = list(state.get("artifacts") or [])
    expected = _compute_expected_delivery(state)
    mismatch = expected > 0 and len(artifacts) != expected
    failure_no_output = len(artifacts) == 0 and bool(errors)
    html_gap = settings.require_html_artifact_upload and _artifacts_missing_required_html_keys(artifacts)
    send_failure_payload = mismatch or failure_no_output or html_gap

    base = settings.go_api_url.rstrip("/")
    url = f"{base}/internal/jobs/{job_id}/complete"
    headers = {
        "Content-Type": "application/json",
        "X-Worker-API-Key": settings.worker_api_key,
    }

    if send_failure_payload:
        removal_keys: list[str] = []
        for a in artifacts:
            sk = (a.get("s3_key") or "").strip()
            if sk:
                removal_keys.append(sk)
            hk = a.get("html_s3_key")
            if hk and str(hk).strip():
                removal_keys.append(str(hk).strip())
        orphan_uploads_to_delete = bool(removal_keys) and (mismatch or html_gap)
        if orphan_uploads_to_delete:
            try:
                await asyncio.to_thread(
                    delete_slide_artifact_keys_sync,
                    settings,
                    removal_keys,
                )
            except Exception as exc:
                logger.error("finalize: slide cleanup failed job_id=%s err=%s", job_id, exc)

        api_error = _failure_message_for_callback(
            errors,
            mismatch_delivery=mismatch,
            html_artifact_delivery_failed=html_gap,
        )
        body: dict[str, object] = {"error": api_error}
        await _post_complete_with_transport_fallback(
            url=url,
            headers=headers,
            json_body=body,
            errors=errors,
            timeout=15.0,
            fallback_timeout=10.0,
        )
        return {"errors": errors, "artifacts": []}

    assistant = _build_assistant_text(state)
    payload: dict[str, object] = {
        "assistantText": assistant,
        "artifacts": [
            {
                "s3Key": a["s3_key"],
                "slideNumber": a["slide_number"],
                "htmlS3Key": a.get("html_s3_key"),
            }
            for a in artifacts
        ],
        "error": None,
    }

    await _post_complete_with_transport_fallback(
        url=url,
        headers=headers,
        json_body=payload,
        errors=errors,
        timeout=15.0,
        fallback_timeout=10.0,
    )

    return {"errors": errors}
