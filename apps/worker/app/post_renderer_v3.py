"""Render V3 posts with image backgrounds and an opaque text surface."""

from html import escape
from typing import AbstractSet

from app.post_document_v2 import PostDocumentV2
from app.post_document_v3 import ImageBackgroundV3, PostDocumentV3, validate_authorized_assets
from app.post_renderer_v2 import render_post_v2
from app.state import SlideItem


RENDERER_VERSION = "3.1.0"


def render_post_v3(document: PostDocumentV3, authorized_assets: AbstractSet[str]) -> list[SlideItem]:
    document = PostDocumentV3.model_validate_json(document.model_dump_json(by_alias=True))
    validate_authorized_assets(document, authorized_assets)
    payload = document.model_dump(mode="json", by_alias=True)
    payload["schemaVersion"] = 2
    payload.pop("credits")
    for slide in payload["slides"]:
        if slide["background"]["type"] == "image":
            slide["background"] = {"type": "solid", "color": {"token": "background"}}
    slides = render_post_v2(PostDocumentV2.model_validate(payload), authorized_assets)
    for index, slide in enumerate(document.slides):
        if not isinstance(slide.background, ImageBackgroundV3):
            continue
        asset = escape(slide.background.asset_id, quote=True)
        html = slides[index]["html"]
        styles = ("body{position:relative;} .photo-background{position:absolute;inset:0;width:100%;height:100%;"
                  "object-fit:cover;} main.hero,main.editorial,main.quote{position:relative;margin:96px;"
                  "width:888px;height:auto;min-height:0;max-height:1158px;overflow:hidden;"
                  f"background:{document.palette.background};padding:64px;}} "
                  "main .image{flex:none;min-height:200px;max-height:400px;}")
        html = html.replace("</style>", styles + "</style>", 1)
        html = html.replace("<body>", f'<body><img class="photo-background" src="attachment://{asset}" alt="" />', 1)
        slides[index] = {**slides[index], "html": html}
    return slides
