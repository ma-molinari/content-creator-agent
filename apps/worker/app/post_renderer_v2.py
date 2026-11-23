"""Render V2 documents using the approved, constrained visual catalog."""

from html import escape
from typing import AbstractSet

from app.post_document import ImageElement
from app.post_document_v2 import Decoration, HexColor, PostDocumentV2, TextElementV2, validate_authorized_assets
from app.post_renderer import _FONTS, _SIZES, _WEIGHTS
from app.state import SlideItem

RENDERER_VERSION = "2.0.0"
_WIDTHS = {"short": "25%", "medium": "50%", "full": "100%"}
_THICKNESSES = {"thin": 4, "medium": 12, "thick": 24}


def resolve_color(document: PostDocumentV2, color) -> str:
    return color.hex if isinstance(color, HexColor) else getattr(document.palette, color.token)


def _luminance(color: str) -> float:
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def validate_post_contrast(document: PostDocumentV2) -> None:
    for slide in document.slides:
        background = resolve_color(document, slide.background.color)
        for element in slide.elements:
            if isinstance(element, TextElementV2):
                color = resolve_color(document, element.style.color)
                lighter, darker = sorted((_luminance(color), _luminance(background)), reverse=True)
                if (lighter + 0.05) / (darker + 0.05) < 4.5:
                    raise ValueError("text contrast is insufficient")


def render_post_v2(document: PostDocumentV2, authorized_assets: AbstractSet[str]) -> list[SlideItem]:
    document = PostDocumentV2.model_validate_json(document.model_dump_json(by_alias=True))
    validate_authorized_assets(document, authorized_assets)
    validate_post_contrast(document)
    slides: list[SlideItem] = []
    for index, slide in enumerate(document.slides, start=1):
        background = resolve_color(document, slide.background.color)
        parts = []
        for element in slide.elements:
            if isinstance(element, TextElementV2):
                color = resolve_color(document, element.style.color)
                style = element.style
                parts.append(f'<div class="element text {element.role}" style="color:{color};'
                             f'font-family:\'{_FONTS[style.font]}\',sans-serif;font-size:{_SIZES[style.size]};'
                             f'font-weight:{_WEIGHTS[style.weight]};text-align:{style.alignment}">'
                             f'{escape(element.content)}</div>')
            elif isinstance(element, ImageElement):
                parts.append(f'<img class="element image" src="attachment://{escape(element.asset_id, quote=True)}" '
                             f'alt="" style="object-fit:{element.fit}" />')
            elif isinstance(element, Decoration):
                height = _THICKNESSES[element.thickness]
                radius = height / 2 if element.corner == "rounded" else 0
                parts.append(f'<div class="element decoration" style="width:{_WIDTHS[element.width]};'
                             f'height:{height}px;border-radius:{radius:g}px;background:{resolve_color(document, element.color)}"></div>')
        content = "".join(parts)
        html = f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;700&family=Inter:wght@400;500;700&display=swap');
* {{ box-sizing:border-box; }}
body {{ margin:0; width:1080px; height:1350px; overflow:hidden; background:{background};
font-family:'Plus Jakarta Sans',sans-serif; }}
main {{ width:100%; height:100%; display:flex; flex-direction:column; gap:32px; padding:96px; }}
.element {{ flex-shrink:0; }}
.text {{ white-space:pre-wrap; overflow-wrap:anywhere; line-height:1.2; }}
.image {{ width:100%; min-height:0; flex:1 1 0; }}
.hero .heading {{ line-height:1.05; }}
.editorial {{ gap:40px; padding:112px; }}
.quote {{ justify-content:center; text-align:center; padding:128px; }}
</style></head><body><main class="{slide.layout}">{content}</main></body></html>'''
        slides.append({"filename": f"slide_{index:02d}.html", "html": html})
    return slides
