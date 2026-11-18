"""Render structured post documents into controlled HTML templates."""

from __future__ import annotations

from html import escape
from typing import AbstractSet

from app.post_document import ImageElement, PostDocumentV1, TextElement
from app.state import SlideItem

RENDERER_VERSION = "1.0.0"

_SIZES = {"small": "32px", "medium": "48px", "large": "72px"}
_WEIGHTS = {"regular": "400", "medium": "500", "bold": "700"}
_FONTS = {"plus_jakarta_sans": "Plus Jakarta Sans", "inter": "Inter"}


def render_post(document: PostDocumentV1, authorized_assets: AbstractSet[str]) -> list[SlideItem]:
    # Pydantic's frozen models still contain mutable lists; validate the whole snapshot again.
    document = PostDocumentV1.model_validate_json(document.model_dump_json(by_alias=True))
    slides: list[SlideItem] = []
    for index, slide in enumerate(document.slides, start=1):
        parts: list[str] = []
        for element in slide.elements:
            if isinstance(element, ImageElement):
                if element.asset_id not in authorized_assets:
                    raise ValueError("image asset is not authorized")
                parts.append(
                    f'<img class="element image" src="attachment://{escape(element.asset_id, quote=True)}" '
                    f'alt="" style="object-fit:{element.fit}" />'
                )
            elif isinstance(element, TextElement):
                style = element.style
                parts.append(
                    f'<div class="element text {element.role}" style="color:{style.color};'
                    f'font-family:\'{_FONTS[style.font]}\',sans-serif;font-size:{_SIZES[style.size]};'
                    f'font-weight:{_WEIGHTS[style.weight]};text-align:{style.alignment}">'
                    f'{escape(element.content)}</div>'
                )
        content = "".join(parts)
        html = f'''<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;700&family=Inter:wght@400;500;700&display=swap');
* {{ box-sizing:border-box; }}
body {{ margin:0; width:1080px; height:1350px; overflow:hidden; background:{slide.background.color};
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
