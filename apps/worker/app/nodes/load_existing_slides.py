"""Load existing slide HTML only for edit/refinement jobs."""

from __future__ import annotations

import asyncio
import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings
from app.nodes.finalize_messages import JOB_FAILURE_REFINEMENT_CONTEXT
from app.state import AgentState, SlideItem, copy_errors

logger = logging.getLogger(__name__)

_MAX_HTML_BYTES = 3_000_000


def _filename_from_key(key: str) -> str:
    base = (key or "").rsplit("/", 1)[-1].strip()
    return base if base.lower().endswith(".html") else f"{base}.html" if base else "slide.html"


def _get_html_bytes_sync(client, bucket: str, key: str) -> bytes:
    obj = client.get_object(Bucket=bucket, Key=key)
    data = obj["Body"].read(_MAX_HTML_BYTES + 1)
    if len(data) > _MAX_HTML_BYTES:
        raise ValueError(f"html object too large key={key!r}")
    return data


async def _fetch_html_slides(keys: list[str], settings, job_id: str) -> list[SlideItem]:
    if not keys:
        return []
    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    bucket = settings.aws_s3_bucket

    async def one(key: str) -> SlideItem | None:
        try:
            raw = await asyncio.to_thread(_get_html_bytes_sync, client, bucket, key)
            return {"filename": _filename_from_key(key), "html": raw.decode("utf-8", errors="replace")}
        except (ClientError, BotoCoreError, ValueError, UnicodeError) as exc:
            logger.error("node=load_existing_slides job_id=%s fetch_html key=%s err=%s", job_id, key, exc)
            return None

    results = await asyncio.gather(*(one(key) for key in keys))
    out = [slide for slide in results if slide is not None]
    if len(out) != len(keys):
        return []
    return out


async def load_existing_slides(state: AgentState) -> dict[str, object]:
    logger.info("node=load_existing_slides job_id=%s", state.get("job_id"))
    intent = state.get("intent_result") or {}
    if intent.get("kind") != "edit":
        return {"existing_slide_html": []}
    sources = list(state.get("existing_slide_sources") or [])
    if sources:
        sources.sort(key=lambda s: int(s.get("slide_number") or 0))
        keys = [str(s.get("html_s3_key") or "") for s in sources if s.get("html_s3_key")]
    else:
        keys = list(state.get("existing_slide_html_s3_keys") or [])
    slides = await _fetch_html_slides(keys, get_settings(), state.get("job_id") or "")
    if not slides or len(slides) != len(keys):
        return {
            "existing_slide_html": [],
            "refinement_context_unavailable": True,
            "errors": copy_errors(state) + [JOB_FAILURE_REFINEMENT_CONTEXT],
        }
    return {
        "existing_slide_html": slides,
        "requested_slide_count": len(slides),
    }


def route_after_load_existing(state: AgentState) -> str:
    return "fail" if state.get("refinement_context_unavailable") else "continue"
