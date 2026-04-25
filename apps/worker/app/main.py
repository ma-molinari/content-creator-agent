"""FastAPI entry: job dispatch and health."""

import logging
from contextlib import asynccontextmanager
from typing import Optional
from uuid import UUID

from dotenv import load_dotenv

load_dotenv()

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
from pydantic import BaseModel

from app.graph import graph
from app.state import AgentState

logger = logging.getLogger(__name__)


class DispatchPayload(BaseModel):
    job_id: UUID
    user_id: UUID
    chat_id: UUID
    raw_message: str = ""
    audit_text: str = ""
    brand_text: str = ""
    reprompt_context: str = ""
    reference_s3_keys: list[str] | None = None


def _initial_state(payload: DispatchPayload) -> AgentState:
    return {
        "job_id": str(payload.job_id),
        "user_id": str(payload.user_id),
        "chat_id": str(payload.chat_id),
        "raw_message": payload.raw_message,
        "audit_text": payload.audit_text,
        "brand_text": payload.brand_text,
        "reprompt_context": payload.reprompt_context or "",
        "reference_s3_keys": list(payload.reference_s3_keys or []),
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
    try:
        await graph.ainvoke(state)
    except Exception:
        logger.exception("job failed: job_id=%s", state.get("job_id"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


app = FastAPI(title="Content Creator Worker", lifespan=lifespan)


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
    background_tasks.add_task(_run_job, state)
    return {"accepted": True, "job_id": str(payload.job_id)}
