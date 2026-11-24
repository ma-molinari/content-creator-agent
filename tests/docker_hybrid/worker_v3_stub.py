"""Worker real com LLM e API Openverse determinísticas para ensaio Docker."""

import base64
import importlib
from pathlib import Path

import httpx
import uvicorn

from app.main import app
from app.post_document_v2 import PostDocumentV2
from app.post_operations_v3 import apply_operations_v3
from app.stock_planning import StockPlan
from app.stock_selection import PhotoChoice
from app.stock_selection import select_stock_image

pipeline = importlib.import_module("app.nodes.structured_pipeline_v3")
stock = importlib.import_module("app.stock_pipeline")
selection = importlib.import_module("app.stock_selection")
renderer = importlib.import_module("app.structured_render")
font = base64.b64encode(Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf").read_bytes()).decode("ascii")
css = "".join("@font-face{font-family:'%s';src:url(data:font/ttf;base64,%s) format('truetype');font-weight:100 900;}" % (name, font) for name in ("Inter", "Plus Jakarta Sans"))


async def local_font(route):
    if route.request.url.startswith("https://fonts.googleapis.com/"):
        await route.fulfill(status=200, content_type="text/css", body=css)
    elif route.request.url.startswith("data:"):
        await route.continue_()
    else:
        await route.abort()


async def generate(**kwargs):
    return PostDocumentV2.model_validate({"schemaVersion": 2, "postType": kwargs["post_type"],
        "palette": {"background": "#FFFFFF", "text": "#000000", "accent": "#000000"},
        "slides": [{"id": "slide", "layout": "hero", "background": {"type": "solid", "color": {"token": "background"}},
                    "elements": [{"id": "title", "type": "text", "role": "heading", "content": "Título inicial",
                                  "style": {"color": {"token": "text"}, "size": "large"}}]}]})


async def plan(*, request, mode, slide_count):
    if mode == "edit" and "troque" not in request.lower():
        return StockPlan(action="none", query=None, slide_number=None)
    return StockPlan(action="replace", query="indisponivel" if "indisponível" in request.lower() else "segunda" if mode == "edit" else "primeira", slide_number=1)


async def edit(*, request, document, authorized_assets, image_action):
    if "título" in request.lower():
        return apply_operations_v3(document, [{"op": "set_text", "slideId": "slide", "elementId": "title", "content": "Título editado"}], authorized_assets)
    return document


def provider(request):
    if request.url.host == "api.openverse.org":
        query = request.url.params["q"]
        if query == "indisponivel":
            return httpx.Response(200, json={"results": []})
        photo = {"id": query, "title": "Foto " + query, "creator": "Pessoa autora", "license": "cc0",
                 "url": "https://upload.wikimedia.org/wikipedia/" + query + ".png",
                 "foreign_landing_url": "https://commons.wikimedia.org/wiki/" + query,
                 "license_url": "https://creativecommons.org/publicdomain/zero/1.0/"}
        return httpx.Response(200, json={"results": [photo]})
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/aXcAAAAASUVORK5CYII=")
    return httpx.Response(200, content=png)


async def select(query, *, client, exclude_sources=frozenset()):
    async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as simulated:
        return await select_stock_image(query, client=simulated, exclude_sources=exclude_sources)


async def analyze(_state):
    return {"attachment_plan": []}


async def choose_photo(_query, _images):
    return PhotoChoice.model_validate({"index": 0, "focalBox": {"left": 20, "top": 10, "right": 80, "bottom": 60}})


pipeline.generate_structured_post_v2 = generate
pipeline.plan_stock_action = plan
pipeline.plan_content_edit_v3 = edit
pipeline.attachment_analyze = analyze
stock.select_stock_image = select
selection._choose_photo = choose_photo
renderer._allow_font_route = local_font
uvicorn.run(app, host="0.0.0.0", port=8000, lifespan="off", log_level="warning")
