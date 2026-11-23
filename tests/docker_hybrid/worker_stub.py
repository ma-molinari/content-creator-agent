"""Run the real worker with deterministic LLM responses and a local test font."""
import asyncio
import base64
import importlib
import json
import logging
from pathlib import Path

import boto3
import uvicorn
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage

from app.main import app
from app.api_client import post_complete_callback
from app.config import get_settings
from app.post_document import PostDocumentV1
from app.post_operations import apply_operations
from app.post_document_v2 import PostDocumentV2, promote_v1
from app.post_operations_v2 import apply_operations_v2

logging.basicConfig(level=logging.INFO)

pipeline = importlib.import_module("app.nodes.structured_pipeline")
render = importlib.import_module("app.structured_render")
visual_direction = importlib.import_module("app.visual_direction")
font = base64.b64encode(Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf").read_bytes()).decode("ascii")
css = "".join(
    "@font-face{font-family:'%s';src:url(data:font/ttf;base64,%s) format('truetype');font-weight:100 900;}" % (name, font)
    for name in ("Inter", "Plus Jakarta Sans")
)


async def local_font(route):
    if route.request.url.startswith("https://fonts.googleapis.com/"):
        await route.fulfill(status=200, content_type="text/css", body=css)
    elif route.request.url.startswith("data:"):
        await route.continue_()
    else:
        await route.abort()


async def generate(**kwargs):
    elements = [{"id": "title", "type": "text", "role": "heading", "content": "Testes automatizados", "style": {"color": "#ffffff", "size": "large"}}]
    if kwargs["authorized_assets"] and "post curto" in kwargs["request"].lower():
        asset = sorted(kwargs["authorized_assets"])[0]
        elements.append({"id": "image", "type": "image", "assetId": asset, "fit": "cover"})
    return PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{
        "id": "slide", "layout": "hero", "background": {"type": "solid", "color": "#142a37"},
        "elements": elements,
    }]})


async def analyze_attachments(_state):
    return {"attachment_plan": []}


async def edit(*, request, document, authorized_assets, **_kwargs):
    if request.startswith("concorrente"):
        await asyncio.sleep(3)
    return apply_operations(document, [{"op": "set_text", "slideId": "slide", "elementId": "title", "content": "Testes com confiança"}], authorized_assets)


async def generate_v2(**kwargs):
    if kwargs["request"] == "Use a referência como inspiração":
        assert not kwargs["authorized_assets"]
    raw = promote_v1(await generate(**kwargs)).model_dump(mode="json", by_alias=True)
    # A new root does not implicitly reuse historical attachments, which may have been removed.
    raw["slides"][0]["elements"] = [element for element in raw["slides"][0]["elements"] if element["type"] != "image"]
    raw["palette"]["accent"] = "#F26930"
    raw["slides"][0]["elements"].insert(0, {"id": "bar", "type": "decoration", "kind": "bar",
        "color": {"token": "accent"}, "width": "full", "thickness": "medium", "corner": "rounded"})
    return PostDocumentV2.model_validate(raw)


async def edit_v2(*, request, document, authorized_assets, **_kwargs):
    if request.startswith("concorrente"):
        await asyncio.sleep(3)
    if request.startswith("Inclua a imagem de referência"):
        used = {item.asset_id for slide in document.slides for item in slide.elements if item.type == "image"}
        available = authorized_assets - used
        assert len(available) == 1
        return apply_operations_v2(document, [{"op": "insert_image", "slideId": "slide", "afterElementId": "title",
            "image": {"id": "explicit-reference", "type": "image", "assetId": next(iter(available)), "fit": "contain"}}], authorized_assets)
    return apply_operations_v2(document, [{"op": "set_text", "slideId": "slide", "elementId": "title", "content": "Testes com confiança V2"}], authorized_assets)


async def reapply(request):
    return "aplicar referências" in request.lower()


class FakeVision:
    def __init__(self, **_kwargs):
        pass

    async def ainvoke(self, _messages):
        return AIMessage(content=json.dumps({"palette": {
            "background": {"status": "observed", "value": "#142A37"},
            "text": {"status": "observed", "value": "#FFFFFF"},
            "accent": {"status": "uncertain", "value": None}}, "decorations": []}))


pipeline.attachment_analyze = analyze_attachments
pipeline.generate_structured_post = generate
pipeline.plan_structured_edit = edit
pipeline.generate_structured_post_v2 = generate_v2
pipeline.plan_structured_edit_v2 = edit_v2
pipeline.requests_reference_reapplication = reapply
visual_direction.ChatOpenAI = FakeVision
render._allow_font_route = local_font

main = importlib.import_module("app.main")
original_run = main._run_job_safe


async def run_with_legacy_stub(state):
    if state.get("post_format") != "legacy_html":
        return await original_run(state)
    # Emulate legacy generation, but retain the real renderer, S3 write and callback.
    document = await generate(request="sem anexo", authorized_assets=set())
    _, images = await render.render_structured_post(document, {})
    settings = get_settings()
    client = boto3.client("s3", region_name=settings.aws_region, aws_access_key_id=settings.aws_access_key_id,
                          aws_secret_access_key=settings.aws_secret_access_key)
    key = f"slides/{state['job_id']}/slide_01.jpeg"
    await asyncio.to_thread(client.put_object, Bucket=settings.aws_s3_bucket, Key=key, Body=images[0]["jpeg_bytes"], ContentType="image/jpeg")
    response = await post_complete_callback(f"{settings.go_api_url.rstrip('/')}/internal/jobs/{state['job_id']}/complete",
        json_body={"assistantText": "Post legado criado.", "artifacts": [{"s3Key": key, "slideNumber": 1}]},
        headers={"X-Worker-API-Key": settings.worker_api_key}, timeout=15.0)
    response.raise_for_status()


main._run_job_safe = run_with_legacy_stub


@app.middleware("http")
async def simulate_old_capability(request, call_next):
    if request.url.path == "/capabilities" and Path("/tmp/visual-v2-incompatible").exists():
        return JSONResponse({"structuredPost": {"contractVersion": 1}})
    return await call_next(request)


uvicorn.run(app, host="0.0.0.0", port=8000, lifespan="off", log_level="warning")
