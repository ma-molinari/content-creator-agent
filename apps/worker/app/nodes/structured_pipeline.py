"""Structured pipeline, isolated from legacy HTML generation."""

from __future__ import annotations

import asyncio
import logging
import re
from uuid import UUID

import boto3

from app.config import get_settings
from app.immutable_assets import copy_version_assets
from app.job_progress import report_job_progress
from app.nodes.attachment_analyze import attachment_analyze
from app.post_document import ImageElement, PostDocumentV1
from app.s3_image_utils import fetch_bytes_limited
from app.state import AgentState
from app.structured_editing import plan_structured_edit
from app.structured_generation import generate_structured_post
from app.structured_render import render_structured_post
from app.structured_upload import send_structured_completion, upload_structured_post

logger = logging.getLogger(__name__)


def _check_base_key(key: str) -> None:
    match = re.fullmatch(r"slides/([0-9a-fA-F-]{36})/document\.json", key)
    if not match:
        raise ValueError("invalid base document key")
    UUID(match.group(1))


def _check_required_assets(document: PostDocumentV1, requirements: list[dict[str, object]]) -> None:
    for item in requirements:
        number = item.get("required_slide_number")
        if isinstance(number, int) and number > 0:
            if number > len(document.slides) or not any(
                isinstance(element, ImageElement) and element.asset_id == item.get("id")
                for element in document.slides[number - 1].elements
            ):
                raise ValueError("required image missing from requested slide")


async def structured_pipeline(state: AgentState) -> dict[str, object]:
    logger.info("node=structured_pipeline job_id=%s", state.get("job_id"))
    settings = get_settings()
    job_id = str(state.get("job_id") or "")
    mode = state.get("generation_mode")
    sources = dict(state.get("authorized_asset_sources") or {})
    client = boto3.client("s3", region_name=settings.aws_region,
                          aws_access_key_id=settings.aws_access_key_id,
                          aws_secret_access_key=settings.aws_secret_access_key)
    await report_job_progress(state, stage="analyzing_attachments", progress=30)
    analyzed = await attachment_analyze(state)
    requirements = [
        {"id": item.get("id"), "description": item.get("description"),
         "required_slide_number": item.get("required_slide_number"), "role": item.get("role")}
        for item in (analyzed.get("attachment_plan") or [])
    ]
    await report_job_progress(state, stage="generating_slides", progress=55)
    if mode == "create":
        document = await generate_structured_post(
            request=state.get("raw_message") or "", profile_text=state.get("profile_text") or "",
            post_type=state.get("chat_post_type") or "", authorized_assets=set(sources),
            requested_slide_count=state.get("requested_slide_count"), asset_requirements=requirements,
        )
    elif mode == "edit":
        key = state.get("document_s3_key") or ""
        _check_base_key(key)
        raw = await asyncio.to_thread(fetch_bytes_limited, client, settings.aws_s3_bucket, key, 2 * 1024 * 1024)
        base = PostDocumentV1.model_validate_json(raw)
        if base.post_type != state.get("chat_post_type"):
            raise ValueError("base post type does not match chat")
        document = await plan_structured_edit(request=state.get("raw_message") or "", document=base,
                                              authorized_assets=set(sources), asset_requirements=requirements)
    else:
        raise ValueError("invalid structured generation mode")
    _check_required_assets(document, requirements)
    await report_job_progress(state, stage="validating_attachments", progress=80)
    copied = await copy_version_assets(document, job_id=job_id, bucket=settings.aws_s3_bucket,
                                       authorized_sources=sources, client=client)
    await report_job_progress(state, stage="rendering_slides", progress=88)
    slides, images = await render_structured_post(document, copied.contents)
    await report_job_progress(state, stage="uploading_assets", progress=95)
    uploaded = await upload_structured_post(document, slides, images, copied, job_id=job_id,
                                            bucket=settings.aws_s3_bucket, client=client)
    await report_job_progress(state, stage="finalizing", progress=98)
    status = await send_structured_completion(
        f"{settings.go_api_url.rstrip('/')}/internal/jobs/{job_id}/complete", api_key=settings.worker_api_key,
        assistant_text="Post atualizado." if mode == "edit" else "Post criado.", upload=uploaded,
    )
    if status == 409:
        logger.info("structured completion conflict job_id=%s", job_id)
    return {}
