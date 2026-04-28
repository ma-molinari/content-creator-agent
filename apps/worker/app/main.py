"""FastAPI entry: job dispatch and health."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional
from uuid import UUID

from dotenv import load_dotenv

load_dotenv()

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from pydantic import BaseModel

from app.graph import graph
from app.slide_count_inference import infer_requested_slide_count
from app.state import AgentState

logger = logging.getLogger(__name__)

_FAILURE_MESSAGE_MAX = 500


def _user_safe_error_message(exc: BaseException) -> str:
    raw = (str(exc) or type(exc).__name__).strip() or "unknown error"
    if len(raw) > _FAILURE_MESSAGE_MAX:
        return raw[: _FAILURE_MESSAGE_MAX - 1] + "…"
    return raw


async def report_job_failure(job_id: UUID, message: str, timeout: float = 15.0) -> None:
    """POST failure to Go API; raises only on request/transport errors (caller logs)."""
    from app.api_client import post_complete_callback
    from app.config import get_settings

    settings = get_settings()
    base = settings.go_api_url.rstrip("/")
    url = f"{base}/internal/jobs/{job_id}/complete"
    headers = {
        "Content-Type": "application/json",
        "X-Worker-API-Key": settings.worker_api_key,
    }
    body = {"error": message}
    try:
        r = await post_complete_callback(url, json_body=body, headers=headers, timeout=timeout)
        if r.status_code >= 400:
            r.raise_for_status()
    except Exception as exc:
        logger.error("failed to report job failure: %s", exc)
        # Don't re-raise; let the caller handle gracefully


class DispatchPayload(BaseModel):
    job_id: UUID
    user_id: UUID
    chat_id: UUID
    raw_message: str = ""
    audit_text: str = ""
    brand_text: str = ""
    reprompt_context: str = ""
    reference_s3_keys: list[str] | None = None
    # Optional: quando a API enviar N explícito; senão o worker infere a partir de raw_message.
    requested_slide_count: int | None = None


def _initial_state(payload: DispatchPayload) -> AgentState:
    n: int | None = payload.requested_slide_count
    if n is None:
        n = infer_requested_slide_count(payload.raw_message)
    return {
        "job_id": str(payload.job_id),
        "user_id": str(payload.user_id),
        "chat_id": str(payload.chat_id),
        "raw_message": payload.raw_message,
        "audit_text": payload.audit_text,
        "brand_text": payload.brand_text,
        "reprompt_context": payload.reprompt_context or "",
        "reference_s3_keys": list(payload.reference_s3_keys or []),
        "requested_slide_count": n,
        "profile_text": "",
        "optimized_brief": "",
        "raw_slide_output": "",
        "slides_html": [],
        "rendered_slides": [],
        "artifacts": [],
        "retry_count": 0,
        "errors": [],
    }


async def _run_job(state: AgentState) -> None:
    jid = state.get("job_id", "")
    logger.info("[railway-debug] graph_start job_id=%s", jid)
    try:
        await graph.ainvoke(state)
        logger.info("[railway-debug] graph_done job_id=%s", jid)
    except Exception as exc:
        logger.exception("job failed: job_id=%s", state.get("job_id"))
        jid = state.get("job_id")
        if not jid:
            return
        try:
            job_uuid = UUID(str(jid))
        except (ValueError, TypeError):
            logger.error("job failed: invalid job_id=%r, cannot report failure", jid)
            return
        msg = _user_safe_error_message(exc)
        try:
            await report_job_failure(job_uuid, msg)
        except Exception as report_exc:
            logger.error(
                "failed to report job failure to API: job_id=%s",
                jid,
                exc_info=report_exc,
            )


async def _run_job_safe(state: AgentState) -> None:
    """Wrapper that ensures the background task never crashes the worker process."""
    try:
        await _run_job(state)
    except Exception as exc:
        logger.critical(
            "background task crashed: job_id=%s",
            state.get("job_id"),
            exc_info=exc,
        )
        # Attempt final error callback to prevent job from being stuck
        try:
            job_id_str = state.get("job_id", "")
            if job_id_str:
                job_uuid = UUID(str(job_id_str))
                await report_job_failure(job_uuid, "worker process error")
        except Exception as report_exc:
            logger.error("failed to report critical error: %s", report_exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.basicConfig(level=logging.INFO)
    logger.info("Worker starting up")
    yield
    # Shutdown: give in-flight background tasks a grace period to complete
    logger.info("Worker shutting down, waiting for in-flight tasks...")
    await asyncio.sleep(5)  # Grace period for background tasks to finish
    logger.info("Worker shutdown complete")


app = FastAPI(
    title="Content Creator Worker",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/jobs", status_code=202)
async def post_jobs(
    payload: DispatchPayload,
    background_tasks: BackgroundTasks,
    x_worker_api_key: Optional[str] = Header(default=None, alias="X-Worker-API-Key"),
):
    from app.config import get_settings

    settings = get_settings()
    key = (x_worker_api_key or "").strip()
    if not key or key != settings.worker_api_key:
        raise HTTPException(status_code=401, detail="invalid worker API key")

    state = _initial_state(payload)
    logger.info(
        "[railway-debug] accepted job_id=%s chat_id=%s user_id=%s",
        payload.job_id,
        payload.chat_id,
        payload.user_id,
    )
    background_tasks.add_task(_run_job_safe, state)
    return {"accepted": True, "job_id": str(payload.job_id)}
