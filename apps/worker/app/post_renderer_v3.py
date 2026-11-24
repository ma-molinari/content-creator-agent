"""Render V3 posts with image backgrounds and a translucent text surface."""

from html import escape
from typing import AbstractSet

from app.post_document_v2 import PostDocumentV2, TextElementV2
from app.post_document_v3 import ImageBackgroundV3, PostDocumentV3, validate_authorized_assets
from app.post_renderer_v2 import _luminance, render_post_v2, resolve_color
from app.state import SlideItem


RENDERER_VERSION = "3.2.1"


def _transparent_surface(document: PostDocumentV3, slide) -> str:
    """Choose a translucent color safe against every possible underlying pixel."""
    background = document.palette.background
    rgb = [int(background[i:i + 2], 16) for i in (1, 3, 5)]
    colors = [resolve_color(document, item.style.color) for item in slide.elements if isinstance(item, TextElementV2)]
    for step in range(65, 100):
        alpha = step / 100
        low = "#" + "".join(f"{int(channel * alpha):02x}" for channel in rgb)
        high = "#" + "".join(f"{min(255, int(channel * alpha + 255 * (1 - alpha) + 0.999999)):02x}" for channel in rgb)
        low_lum, high_lum = _luminance(low), _luminance(high)
        def contrast(color: str) -> float:
            text_lum = _luminance(color)
            if low_lum <= text_lum <= high_lum:
                return 1.0
            return min((max(text_lum, value) + 0.05) / (min(text_lum, value) + 0.05)
                       for value in (low_lum, high_lum))
        if all(contrast(color) >= 4.5 for color in colors):
            return f"rgba({rgb[0]},{rgb[1]},{rgb[2]},{alpha:.2f})"
    raise ValueError("transparent background cannot guarantee text contrast")


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
        surface = _transparent_surface(document, slide)
        asset = escape(slide.background.asset_id, quote=True)
        html = slides[index]["html"]
        styles = ("body{position:relative;display:flow-root;} .photo-background{position:absolute;inset:0;width:100%;height:100%;"
                  "object-fit:cover;} main.hero,main.editorial,main.quote{position:relative;margin:96px;"
                  "width:888px;height:auto;min-height:0;max-height:1158px;overflow:hidden;"
                  f"background:{surface};padding:64px;}} "
                  "main .image{flex:none;min-height:200px;max-height:400px;}")
        html = html.replace("</style>", styles + "</style>", 1)
        html = html.replace("<body>", f'<body><img class="photo-background" src="attachment://{asset}" alt="" />', 1)
        slides[index] = {**slides[index], "html": html}
    return slides
