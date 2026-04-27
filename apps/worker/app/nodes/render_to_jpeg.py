"""Render each slide HTML to JPEG bytes with Playwright."""

import logging

from playwright.async_api import async_playwright

from app.state import AgentState, RenderedSlide

logger = logging.getLogger(__name__)

_VIEWPORT = {"width": 1080, "height": 1350}
_JPEG_QUALITY = 92
_TIMEOUT_MS = 60_000


async def render_to_jpeg(state: AgentState) -> dict:
    logger.info("node=render_to_jpeg job_id=%s", state.get("job_id"))
    slides = state.get("slides_html") or []
    errors = list(state.get("errors") or [])
    rendered: list[RenderedSlide] = []

    if not slides:
        return {"rendered_slides": [], "errors": errors}

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        try:
            for item in slides:
                fname = item.get("filename") or "slide.html"
                html = item.get("html") or ""
                try:
                    page = await browser.new_page()
                    await page.set_viewport_size(_VIEWPORT)
                    await page.set_content(html, wait_until="networkidle", timeout=_TIMEOUT_MS)
                    data = await page.screenshot(
                        type="jpeg",
                        quality=_JPEG_QUALITY,
                        full_page=False,
                    )
                    await page.close()
                    base = fname.rsplit(".", 1)[0] if "." in fname else fname
                    jpeg_name = f"{base}.jpeg"
                    rendered.append({"filename": jpeg_name, "jpeg_bytes": data})
                except Exception as exc:  # noqa: BLE001 — capture Playwright errors per slide
                    errors.append(f"render_to_jpeg {fname}: {exc!s}")
        finally:
            await browser.close()

    return {"rendered_slides": rendered, "errors": errors}
