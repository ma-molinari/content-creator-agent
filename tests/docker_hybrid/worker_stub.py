"""Run the real worker with deterministic LLM responses and a local test font."""
import base64
import importlib
from pathlib import Path

import uvicorn

from app.main import app
from app.post_document import PostDocumentV1
from app.post_operations import apply_operations

pipeline = importlib.import_module("app.nodes.structured_pipeline")
render = importlib.import_module("app.structured_render")
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


async def generate(**_kwargs):
    return PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{
        "id": "slide", "layout": "hero", "background": {"type": "solid", "color": "#142a37"},
        "elements": [{"id": "title", "type": "text", "role": "heading", "content": "Testes automatizados", "style": {"color": "#ffffff", "size": "large"}}],
    }]})


async def edit(*, document, authorized_assets, **_kwargs):
    return apply_operations(document, [{"op": "set_text", "slideId": "slide", "elementId": "title", "content": "Testes com confiança"}], authorized_assets)


pipeline.generate_structured_post = generate
pipeline.plan_structured_edit = edit
render._allow_font_route = local_font
uvicorn.run(app, host="0.0.0.0", port=8000, lifespan="off", log_level="warning")
