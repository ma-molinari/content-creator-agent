"""FastAPI entry: job dispatch and health."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import UUID
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException

from app.graph import graph
from app.job_payload import DispatchPayload, initial_state
from app.state import AgentState
from app.structured_upload import StructuredCallbackUnknown
from app.structured_editing import StructuredEditingError

logger = logging.getLogger(__name__)

_FAILURE_MESSAGE_MAX = 500


def _user_safe_error_message(exc: BaseException) -> str:
    raw = (str(exc) or type(exc).__name__).strip() or "unknown error"
    if len(raw) > _FAILURE_MESSAGE_MAX:
        return raw[: _FAILURE_MESSAGE_MAX - 1] + "…"
    return raw


async def report_job_failure(job_id: UUID, message: str, timeout: float = 15.0, *, error_code: str = "worker_exception") -> None:
    """POST failure to Go API. Logs on HTTP/transport failure; does not raise."""
    from app.api_client import post_complete_callback
    from app.config import get_settings

    settings = get_settings()
    base = settings.go_api_url.rstrip("/")
    url = f"{base}/internal/jobs/{job_id}/complete"
    headers = {
        "Content-Type": "application/json",
        "X-Worker-API-Key": settings.worker_api_key,
    }
    body = {"error": message, "errorCode": error_code}
    try:
        r = await post_complete_callback(url, json_body=body, headers=headers, timeout=timeout)
        if r.status_code >= 400:
            r.raise_for_status()
    except Exception as exc:
        logger.error("failed to report job failure: %s", exc)
        # Don't re-raise; let the caller handle gracefully


async def _run_job(state: AgentState) -> None:
    jid = state.get("job_id", "")
    logger.debug("graph_start job_id=%s", jid)
    try:
        await graph.ainvoke(state)
        logger.debug("graph_done job_id=%s", jid)
    except StructuredCallbackUnknown:
        logger.warning("structured callback outcome unknown job_id=%s", state.get("job_id"))
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
        if isinstance(exc, StructuredEditingError):
            await report_job_failure(job_uuid, "Não foi possível aplicar a edição. Reformule o pedido.", error_code="EDIT_UNSUPPORTED")
        elif state.get("post_format") == "structured_v1":
            await report_job_failure(job_uuid, "Não foi possível gerar o post estruturado. Tente novamente.")
        else:
            await report_job_failure(job_uuid, _user_safe_error_message(exc))


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
    logging.basicConfig(level=logging.INFO)
    logger.info("Worker starting up")
    yield
    # Brief grace window so accepted background jobs can finish during shutdown.
    logger.info("Worker shutting down, waiting for in-flight tasks...")
    await asyncio.sleep(5)  # Grace period for background tasks to finish
    logger.info("Worker shutdown complete")


app = FastAPI(
    title="Post Mind Worker",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.get("/health")
def health():
    return {"status": "ok"}


def _require_worker_key(raw_key: Optional[str]) -> None:
    from app.config import get_settings

    key = (raw_key or "").strip()
    if not key or key != get_settings().worker_api_key:
        raise HTTPException(status_code=401, detail="invalid worker API key")


@app.get("/capabilities")
def capabilities(x_worker_api_key: Optional[str] = Header(default=None, alias="X-Worker-API-Key")):
    _require_worker_key(x_worker_api_key)
    return {"structuredPost": {"contractVersion": 1}}


def _accept_job(payload: DispatchPayload, background_tasks: BackgroundTasks) -> dict[str, object]:
    state = initial_state(payload)
    logger.debug("job accepted job_id=%s chat_id=%s user_id=%s", payload.job_id, payload.chat_id, payload.user_id)
    background_tasks.add_task(_run_job_safe, state)
    return {"accepted": True, "job_id": str(payload.job_id)}


@app.post("/jobs", status_code=202)
async def post_jobs(
    payload: DispatchPayload,
    background_tasks: BackgroundTasks,
    x_worker_api_key: Optional[str] = Header(default=None, alias="X-Worker-API-Key"),
):
    _require_worker_key(x_worker_api_key)
    if payload.post_format != "legacy_html":
        raise HTTPException(status_code=400, detail="invalid job format")
    return _accept_job(payload, background_tasks)


@app.post("/jobs/structured", status_code=202)
async def post_structured_jobs(
    payload: DispatchPayload,
    background_tasks: BackgroundTasks,
    x_worker_api_key: Optional[str] = Header(default=None, alias="X-Worker-API-Key"),
):
    _require_worker_key(x_worker_api_key)
    if payload.post_format != "structured_v1":
        raise HTTPException(status_code=400, detail="invalid job format")
    return _accept_job(payload, background_tasks)
