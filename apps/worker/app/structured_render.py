"""Render validated structured slides and reject missing assets or clipped content."""

from __future__ import annotations

import base64
import logging
from typing import Mapping
from time import monotonic
from urllib.parse import urlsplit

from playwright.async_api import Route, async_playwright

from app.nodes.contrast_fix import _CONTRAST_FIX_JS
from app.post_document import ImageElement, PostDocumentV1, TextElement
from app.post_renderer import render_post
from app.post_document_v2 import PostDocumentV2
from app.post_document_v3 import ImageBackgroundV3, PostDocumentV3, used_asset_ids as used_v3_assets
from app.post_renderer_v3 import render_post_v3
from app.post_renderer_v2 import render_post_v2
from app.slide_asset_wait import wait_for_slide_images
from app.slide_design_checks import collect_design_violations
from app.state import RenderedSlide, SlideItem

_ALLOWED_HOSTS = frozenset({"fonts.googleapis.com", "fonts.gstatic.com"})
_FONT_NAMES = {"plus_jakarta_sans": "Plus Jakarta Sans", "inter": "Inter"}
logger = logging.getLogger(__name__)


async def _allow_font_route(route: Route) -> None:
    url = route.request.url
    parsed = urlsplit(url)
    if url.startswith("data:") or (parsed.scheme == "https" and parsed.hostname in _ALLOWED_HOSTS):
        await route.continue_()
    else:
        await route.abort()


def _image_data_url(data: bytes) -> str:
    if data.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif data.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        mime = "image/webp"
    else:
        raise ValueError("unsupported image content")
    if len(data) > 5 * 1024 * 1024:
        raise ValueError("image exceeds size limit")
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


async def render_structured_post(
    document: PostDocumentV1 | PostDocumentV2 | PostDocumentV3, authorized_assets: Mapping[str, bytes],
) -> tuple[list[SlideItem], list[RenderedSlide]]:
    is_v3 = isinstance(document, PostDocumentV3)
    is_v2 = isinstance(document, PostDocumentV2) and not is_v3
    started = monotonic()
    try:
        slides = (render_post_v3(document, set(authorized_assets)) if is_v3 else
                  render_post_v2(document, set(authorized_assets)) if is_v2 else
                  render_post(document, set(authorized_assets)))
    except ValueError as exc:
        if is_v2:
            reason = "contrast" if str(exc) == "text contrast is insufficient" else "validation"
            logger.info("[metrics] event=structured_validation schema=2 outcome=failed reason=%s duration_ms=%d", reason, int((monotonic() - started) * 1000))
        raise
    if is_v2:
        logger.info("[metrics] event=structured_validation schema=2 outcome=success duration_ms=%d", int((monotonic() - started) * 1000))
    used_asset_ids = (used_v3_assets(document) if is_v3 else
                      {item.asset_id for slide in document.slides for item in slide.elements if isinstance(item, ImageElement)})
    image_urls = {key: _image_data_url(authorized_assets[key]) + f"#asset-{key}" for key in used_asset_ids}
    fixed_slides: list[SlideItem] = []
    images: list[RenderedSlide] = []
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(args=["--disable-background-networking", "--disable-extensions", "--no-default-browser-check"])
        try:
            for index, slide in enumerate(slides):
                html = slide["html"]
                violations = collect_design_violations(html)
                if violations:
                    if is_v2:
                        logger.info("[metrics] event=structured_render schema=2 outcome=failed reason=validation duration_ms=%d", int((monotonic() - started) * 1000))
                    raise ValueError("structured slide failed static design validation")
                inline_html = html
                references: dict[str, str] = {}
                for item in document.slides[index].elements:
                    if isinstance(item, ImageElement):
                        reference = f"attachment://{item.asset_id}"
                        data_url = image_urls[item.asset_id]
                        inline_html = inline_html.replace(f'src="{reference}"', f'src="{data_url}"')
                        references[data_url] = reference
                background = document.slides[index].background
                if is_v3 and isinstance(background, ImageBackgroundV3):
                    reference = f"attachment://{background.asset_id}"
                    data_url = image_urls[background.asset_id]
                    inline_html = inline_html.replace(f'src="{reference}"', f'src="{data_url}"')
                    references[data_url] = reference
                page = await browser.new_page(viewport={"width": 1080, "height": 1350})
                try:
                    await page.route("**/*", _allow_font_route)
                    await page.set_content(inline_html, wait_until="load", timeout=60_000)
                    fonts = sorted({_FONT_NAMES[item.style.font] for item in document.slides[index].elements if isinstance(item, TextElement)})
                    fonts_ok = await page.evaluate("""async fonts => {
                        await document.fonts.ready;
                        for (const family of fonts) {
                            const faces = await document.fonts.load(`16px '${family}'`);
                            if (!faces.length || faces.some(face => face.status !== 'loaded')) return false;
                        }
                        return true;
                    }""", fonts)
                    if not fonts_ok:
                        if is_v2:
                            logger.info("[metrics] event=structured_render schema=2 outcome=failed reason=font duration_ms=%d", int((monotonic() - started) * 1000))
                        raise ValueError("required font unavailable")
                    await wait_for_slide_images(page)
                    clipped = await page.evaluate("""safeArea => {
                        const main = document.querySelector('main');
                        const bounds = main.getBoundingClientRect();
                        const style = getComputedStyle(main);
                        const left = bounds.left + (safeArea ? parseFloat(style.paddingLeft) : 0);
                        const right = bounds.right - (safeArea ? parseFloat(style.paddingRight) : 0);
                        const top = bounds.top + (safeArea ? parseFloat(style.paddingTop) : 0);
                        const bottom = bounds.bottom - (safeArea ? parseFloat(style.paddingBottom) : 0);
                        return [...main.querySelectorAll('.element')].some(el => {
                            const box = el.getBoundingClientRect();
                            const style = getComputedStyle(el);
                            const clipsX = style.overflowX !== 'visible';
                            const clipsY = style.overflowY !== 'visible';
                            return box.left < left - 1 || box.top < top - 1 ||
                                box.right > right + 1 || box.bottom > bottom + 1 ||
                                (el.scrollWidth > el.clientWidth + 1 &&
                                    (clipsX || box.left + el.scrollWidth > right + 1)) ||
                                (el.scrollHeight > el.clientHeight + 1 &&
                                    (clipsY || box.top + el.scrollHeight > bottom + 1));
                        });
                    }""", is_v2 or is_v3)
                    if clipped:
                        if is_v2:
                            logger.info("[metrics] event=structured_render schema=2 outcome=failed reason=overflow duration_ms=%d", int((monotonic() - started) * 1000))
                        raise ValueError("slide content exceeds canvas")
                    result = await page.evaluate(_CONTRAST_FIX_JS) if not (is_v2 or is_v3) else None
                    fixed_html = await page.content() if result and result.get("hadViolations") else html
                    for data_url, reference in references.items():
                        fixed_html = fixed_html.replace(data_url, reference)
                    jpeg = await page.screenshot(type="jpeg", quality=92, full_page=False)
                    fixed_slides.append({"filename": slide["filename"], "html": fixed_html})
                    images.append({"filename": slide["filename"].rsplit(".", 1)[0] + ".jpeg", "jpeg_bytes": jpeg})
                finally:
                    await page.close()
        finally:
            await browser.close()
    if is_v2:
        logger.info("[metrics] event=structured_render schema=2 outcome=success slides=%d duration_ms=%d", len(images), int((monotonic() - started) * 1000))
    return fixed_slides, images
