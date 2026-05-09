"""Best-effort job progress callbacks to the Go API."""

from __future__ import annotations

import logging
from uuid import UUID

from app.api_client import post_progress_callback
from app.config import get_settings
from app.state import AgentState

logger = logging.getLogger(__name__)


async def report_job_progress(state: AgentState, *, stage: str, progress: int) -> None:
    job_id = str(state.get("job_id") or "").strip()
    if not job_id:
        return
    try:
        UUID(job_id)
    except (TypeError, ValueError):
        return

    settings = get_settings()
    base = settings.go_api_url.rstrip("/")
    url = f"{base}/internal/jobs/{job_id}/progress"
    headers = {
        "Content-Type": "application/json",
        "X-Worker-API-Key": settings.worker_api_key,
    }
    body = {"stage": stage, "progress": progress}
    try:
        r = await post_progress_callback(url, json_body=body, headers=headers)
        if r.status_code >= 400:
            logger.warning(
                "progress callback HTTP error job_id=%s stage=%s status=%s",
                job_id,
                stage,
                r.status_code,
            )
    except Exception as exc:
        logger.warning(
            "progress callback failed job_id=%s stage=%s err=%s",
            job_id,
            stage,
            exc,
        )
