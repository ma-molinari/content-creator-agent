"""Render each slide HTML to JPEG bytes with Playwright."""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import urlparse

from playwright.async_api import Browser, Route, async_playwright

from app.config import get_settings
from app.slide_render_html import enhance_slide_html_for_render
from app.state import AgentState, RenderedSlide, SlideItem, copy_errors

logger = logging.getLogger(__name__)

_VIEWPORT = {"width": 1080, "height": 1350}
_JPEG_QUALITY = 92
_TIMEOUT_MS = 60_000

_ALLOWED_S3_HOSTS: frozenset[str] | None = None


def _allowed_s3_hosts() -> frozenset[str]:
    global _ALLOWED_S3_HOSTS
    if _ALLOWED_S3_HOSTS is None:
        s = get_settings()
        _ALLOWED_S3_HOSTS = frozenset(
            {
                f"{s.aws_s3_bucket}.s3.{s.aws_region}.amazonaws.com",
                f"{s.aws_s3_bucket}.s3.amazonaws.com",
                f"s3.{s.aws_region}.amazonaws.com",
            }
        )
    return _ALLOWED_S3_HOSTS


async def _allow_slide_route(route: Route) -> None:
    """Block remote assets except Google Fonts (needed for @import in slide HTML)."""
    url = route.request.url
    if url.startswith("data:"):
        await route.continue_()
        return
    if "fonts.googleapis.com" in url or "fonts.gstatic.com" in url:
        await route.continue_()
        return
    host = urlparse(url).hostname
    if host and host in _allowed_s3_hosts():
        await route.continue_()
        return
    await route.abort()


async def _render_one_slide(browser: Browser, item: SlideItem) -> tuple[RenderedSlide | None, str | None]:
    fname = item.get("filename") or "slide.html"
    raw_html = item.get("html") or ""
    html = enhance_slide_html_for_render(raw_html)
    try:
        page = await browser.new_page()
        try:
            await page.set_viewport_size(_VIEWPORT)
            await page.route("**/*", _allow_slide_route)
            await page.set_content(html, wait_until="domcontentloaded", timeout=_TIMEOUT_MS)
            try:
                await page.evaluate("() => document.fonts.ready")
            except Exception as exc:
                logger.debug("render_to_jpeg: document.fonts.ready skipped (%s)", exc)
            data = await page.screenshot(
                type="jpeg",
                quality=_JPEG_QUALITY,
                full_page=False,
            )
        finally:
            await page.close()
        base = fname.rsplit(".", 1)[0] if "." in fname else fname
        jpeg_name = f"{base}.jpeg"
        return ({"filename": jpeg_name, "jpeg_bytes": data}, None)
    except Exception as exc:  # noqa: BLE001 — capture Playwright errors per slide
        return (None, f"render_to_jpeg {fname}: {exc!s}")


async def render_to_jpeg(state: AgentState) -> dict:
    logger.info("node=render_to_jpeg job_id=%s", state.get("job_id"))
    slides = state.get("slides_html") or []
    errors = copy_errors(state)
    rendered: list[RenderedSlide] = []

    if not slides:
        return {"rendered_slides": [], "errors": errors}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=[
                "--disable-background-networking",
                "--disable-extensions",
                "--no-default-browser-check",
            ]
        )
        try:
            results = await asyncio.gather(
                *[_render_one_slide(browser, item) for item in slides],
            )
        finally:
            await browser.close()

    for slide_or_none, err in results:
        if err:
            errors.append(err)
        elif slide_or_none is not None:
            rendered.append(slide_or_none)

    return {"rendered_slides": rendered, "errors": errors}
