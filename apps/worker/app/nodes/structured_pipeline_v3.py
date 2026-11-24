"""Generate and edit V3 snapshots with Openverse background images."""

import asyncio
import json

import boto3
import httpx

from app.config import get_settings
from app.immutable_assets import copy_version_assets
from app.job_progress import report_job_progress
from app.nodes.attachment_analyze import attachment_analyze
from app.nodes.structured_pipeline import _check_base_key, _check_required_assets
from app.post_document import PostDocumentV1
from app.post_document_v2 import PostDocumentV2
from app.post_document_v3 import PostDocumentV3, promote_to_v3
from app.post_renderer_v3 import RENDERER_VERSION
from app.s3_image_utils import fetch_bytes_limited
from app.state import AgentState
from app.stock_pipeline import apply_stock_image
from app.stock_planning import plan_stock_action
from app.structured_editing_v3 import plan_content_edit_v3
from app.structured_generation import generate_structured_post_v2
from app.structured_render import render_structured_post
from app.structured_upload import send_structured_completion, upload_structured_post


async def structured_pipeline_v3(state: AgentState) -> dict[str, object]:
    settings = get_settings()
    job_id = str(state.get("job_id") or "")
    mode = state.get("generation_mode")
    request = state.get("raw_message") or ""
    sources = dict(state.get("authorized_asset_sources") or {})
    client = boto3.client("s3", region_name=settings.aws_region, aws_access_key_id=settings.aws_access_key_id,
                          aws_secret_access_key=settings.aws_secret_access_key)
    await report_job_progress(state, stage="analyzing_attachments", progress=30)
    analyzed = await attachment_analyze(state)
    requirements = [{"id": item.get("id"), "description": item.get("description"),
                     "required_slide_number": item.get("required_slide_number"), "role": item.get("role")}
                    for item in (analyzed.get("attachment_plan") or [])]
    await report_job_progress(state, stage="generating_slides", progress=55)
    if mode == "create":
        base = await generate_structured_post_v2(request=request, profile_text=state.get("profile_text") or "",
                 post_type=state.get("chat_post_type") or "", authorized_assets=set(sources),
                 requested_slide_count=state.get("requested_slide_count"), asset_requirements=requirements)
        document = promote_to_v3(base)
    elif mode == "edit":
        key = state.get("document_s3_key") or ""
        _check_base_key(key)
        raw = await asyncio.to_thread(fetch_bytes_limited, client, settings.aws_s3_bucket, key, 2 * 1024 * 1024)
        schema = json.loads(raw).get("schemaVersion")
        if type(schema) is not int or schema not in (1, 2, 3):
            raise ValueError("invalid base schema")
        document = (promote_to_v3(PostDocumentV1.model_validate_json(raw)) if schema == 1 else
                    promote_to_v3(PostDocumentV2.model_validate_json(raw)) if schema == 2 else
                    PostDocumentV3.model_validate_json(raw))
        if document.post_type != state.get("chat_post_type"):
            raise ValueError("base post type does not match chat")
    else:
        raise ValueError("invalid structured generation mode")
    plan = await plan_stock_action(request=request, mode=mode, slide_count=len(document.slides))
    if mode == "edit":
        document = await plan_content_edit_v3(request=request, document=document, authorized_assets=set(sources),
                                              image_action=plan.action == "replace")
    async with httpx.AsyncClient() as http:
        document, selected = await apply_stock_image(document, request=request, mode=mode,
                                                      authorized_assets=set(sources), client=http, plan=plan)
    _check_required_assets(document, requirements)
    await report_job_progress(state, stage="validating_attachments", progress=80)
    copied = await copy_version_assets(document, job_id=job_id, bucket=settings.aws_s3_bucket,
                                       authorized_sources=sources, selected_assets=selected, client=client)
    await report_job_progress(state, stage="rendering_slides", progress=88)
    slides, images = await render_structured_post(document, copied.contents)
    await report_job_progress(state, stage="uploading_assets", progress=95)
    uploaded = await upload_structured_post(document, slides, images, copied, job_id=job_id,
                                             bucket=settings.aws_s3_bucket, client=client)
    await report_job_progress(state, stage="finalizing", progress=98)
    text = "Post atualizado." if mode == "edit" else "Post criado."
    if document.credits:
        text += "\n\nImagens: " + "; ".join(f"{c.title or 'Imagem'} — {c.creator or 'autoria não informada'} — {c.source_url} — {c.license_url}" for c in document.credits.values())
        text += "\nConfira as informações de licença na página de origem."
    await send_structured_completion(f"{settings.go_api_url.rstrip('/')}/internal/jobs/{job_id}/complete",
                                    api_key=settings.worker_api_key, assistant_text=text, upload=uploaded,
                                    schema_version=3, renderer_version=RENDERER_VERSION)
    return {}
