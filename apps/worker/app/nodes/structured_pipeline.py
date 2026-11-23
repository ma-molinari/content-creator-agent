"""Structured pipeline, isolated from legacy HTML generation."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from uuid import UUID
from time import monotonic

import boto3

from app.config import get_settings
from app.immutable_assets import copy_version_assets
from app.job_progress import report_job_progress
from app.nodes.attachment_analyze import attachment_analyze
from app.post_document import ImageElement, PostDocumentV1
from app.post_document_v2 import PostDocumentV2, Decoration, promote_v1
from app.s3_image_utils import fetch_bytes_limited
from app.state import AgentState
from app.structured_editing import plan_structured_edit, plan_structured_edit_v2
from app.structured_generation import generate_structured_post, generate_structured_post_v2
from app.post_renderer_v2 import RENDERER_VERSION as RENDERER_VERSION_V2
from app.reference_policy import ReferenceSelectionError, selected_references, validate_reference_usage
from app.visual_direction import extract_visual_direction, requests_reference_reapplication
from app.structured_render import render_structured_post
from app.structured_upload import send_structured_completion, upload_structured_post

logger = logging.getLogger(__name__)


def _check_base_key(key: str) -> None:
    match = re.fullmatch(r"slides/([0-9a-fA-F-]{36})/document\.json", key)
    if not match:
        raise ValueError("invalid base document key")
    UUID(match.group(1))


def _check_required_assets(document: PostDocumentV1 | PostDocumentV2, requirements: list[dict[str, object]]) -> None:
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
    started = monotonic()
    v2 = state.get("target_schema_version") == 2
    sources = dict(state.get("authorized_asset_sources") or {})
    reference_sources = state.get("reference_asset_sources")
    reference_keys = list(state.get("reference_s3_keys") or [])
    if reference_sources is None and reference_keys:
        raise ReferenceSelectionError("Atualize a API e o worker para usar as referências com segurança.")
    references = dict(reference_sources or {})
    selected = selected_references(state.get("raw_message") or "", references, reference_keys)
    for asset_id, key in references.items():
        if sources.get(asset_id) == key:
            sources.pop(asset_id)
    for asset_id in selected:
        sources.setdefault(asset_id, references[asset_id])
    base = None
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
    if mode == "create" and v2:
        direction = await extract_visual_direction(user_id=str(state.get("user_id") or ""), reference_keys=list(state.get("reference_s3_keys") or []))
        document = await generate_structured_post_v2(
            request=state.get("raw_message") or "", profile_text=state.get("profile_text") or "",
            post_type=state.get("chat_post_type") or "", authorized_assets=set(sources), visual_direction=direction,
            requested_slide_count=state.get("requested_slide_count"), asset_requirements=requirements,
        )
    elif mode == "create":
        document = await generate_structured_post(
            request=state.get("raw_message") or "", profile_text=state.get("profile_text") or "",
            post_type=state.get("chat_post_type") or "", authorized_assets=set(sources),
            requested_slide_count=state.get("requested_slide_count"), asset_requirements=requirements,
        )
    elif mode == "edit":
        key = state.get("document_s3_key") or ""
        _check_base_key(key)
        raw = await asyncio.to_thread(fetch_bytes_limited, client, settings.aws_s3_bucket, key, 2 * 1024 * 1024)
        if v2:
            schema = json.loads(raw).get("schemaVersion")
            if type(schema) is not int or schema not in (1, 2):
                raise ValueError("invalid base schema")
            base = promote_v1(PostDocumentV1.model_validate_json(raw)) if schema == 1 else PostDocumentV2.model_validate_json(raw)
        else:
            base = PostDocumentV1.model_validate_json(raw)
        if base.post_type != state.get("chat_post_type"):
            raise ValueError("base post type does not match chat")
        if v2:
            reapply = await requests_reference_reapplication(state.get("raw_message") or "")
            direction = await extract_visual_direction(user_id=str(state.get("user_id") or ""),
                reference_keys=list(state.get("reference_s3_keys") or []), reapply=True) if reapply else None
            document = await plan_structured_edit_v2(request=state.get("raw_message") or "", document=base,
                authorized_assets=set(sources), asset_requirements=requirements, reapply_references=reapply, visual_direction=direction)
        else:
            document = await plan_structured_edit(request=state.get("raw_message") or "", document=base,
                                                  authorized_assets=set(sources), asset_requirements=requirements)
    else:
        raise ValueError("invalid structured generation mode")
    validate_reference_usage(document, base, set(references), selected)
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
    completion_kwargs = {"schema_version": 2, "renderer_version": RENDERER_VERSION_V2} if v2 else {}
    status = await send_structured_completion(
        f"{settings.go_api_url.rstrip('/')}/internal/jobs/{job_id}/complete", api_key=settings.worker_api_key,
        assistant_text="Post atualizado." if mode == "edit" else "Post criado.", upload=uploaded, **completion_kwargs,
    )
    if v2:
        count = sum(isinstance(element, Decoration) for slide in document.slides for element in slide.elements)
        logger.info("[metrics] event=structured_publication schema=2 outcome=%s decorations=%d duration_ms=%d", "conflict" if status == 409 else "success", count, int((monotonic() - started) * 1000))
    if status == 409:
        logger.info("structured completion conflict job_id=%s", job_id)
    return {}
