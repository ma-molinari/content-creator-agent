"""Apply contrast fixes and render JPEGs in one Playwright pass."""

from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from playwright.async_api import Browser, Route, async_playwright

from app.config import get_settings
from app.nodes.contrast_fix import _CONTRAST_FIX_JS
from app.s3_image_utils import fetch_bytes_limited, guess_mime, is_allowed_s3_url
from app.slide_asset_wait import wait_for_slide_images
from app.slide_render_html import enhance_slide_html_for_render
from app.state import AgentState, RenderedSlide, SlideItem, copy_errors

logger = logging.getLogger(__name__)

_VIEWPORT = {"width": 1080, "height": 1350}
_JPEG_QUALITY = 92
_TIMEOUT_MS = 60_000


@dataclass(frozen=True)
class _InlineReplacement:
    source_url: str
    data_url: str
    source_refs: tuple[str, ...] = ()


async def _allow_slide_route(route: Route) -> None:
    url = route.request.url
    if url.startswith("data:") or "fonts.googleapis.com" in url or "fonts.gstatic.com" in url or is_allowed_s3_url(url):
        await route.continue_()
        return
    await route.abort()


def _inline_attachment_urls(html: str, replacements: list[_InlineReplacement]) -> str:
    out = html
    for repl in replacements:
        source_urls = _source_url_variants(repl.source_url) + list(repl.source_refs)
        for source_url in source_urls:
            out = out.replace(source_url, repl.data_url)
            out = out.replace(source_url.replace("&", "&amp;"), repl.data_url)
    return out


def _restore_attachment_urls(html: str, replacements: list[_InlineReplacement]) -> str:
    out = html
    for repl in replacements:
        stable_ref = repl.source_refs[0] if repl.source_refs else repl.source_url
        out = out.replace(repl.data_url, stable_ref)
    return out


def _source_url_variants(source_url: str) -> list[str]:
    if not source_url:
        return []
    out = [source_url]
    try:
        parts = urlsplit(source_url)
    except ValueError:
        return out
    if parts.query or parts.fragment:
        without_query = urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
        if without_query and without_query not in out:
            out.append(without_query)
    return out


def _fetch_attachment_data_url(client, bucket: str, key: str, max_bytes: int) -> str:
    blob = fetch_bytes_limited(client, bucket, key, max_bytes)
    mime = guess_mime(blob, key)
    b64 = base64.standard_b64encode(blob).decode("ascii")
    return f"data:{mime};base64,{b64}"


async def _build_inline_replacements(state: AgentState) -> tuple[list[_InlineReplacement], list[str]]:
    plan = list(state.get("attachment_plan") or [])
    known = list(state.get("known_attachments") or [])
    if not plan and not known:
        return [], []
    settings = get_settings()
    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    bucket = settings.aws_s3_bucket
    max_bytes = settings.reference_image_max_bytes
    replacements: list[_InlineReplacement] = []
    errors: list[str] = []
    seen_ids: set[str] = set()
    seen_keys: set[str] = set()

    sources: list[dict[str, object]] = []

    def add_source(item: dict[str, object], *, default_render_ref: bool) -> None:
        item_id = str(item.get("id") or "").strip()
        key = str(item.get("s3_key") or "").strip()
        if not key or key in seen_keys or (item_id and item_id in seen_ids):
            return
        seen_keys.add(key)
        if item_id:
            seen_ids.add(item_id)
        render_ref = str(item.get("render_ref") or "").strip()
        if not render_ref and default_render_ref and item_id:
            render_ref = f"attachment://{item_id}"
        sources.append(
            {
                "id": item_id,
                "s3_key": key,
                "url": str(item.get("url") or "").strip(),
                "render_ref": render_ref,
            }
        )

    for item in plan:
        add_source(item, default_render_ref=True)
    for item in known:
        add_source(item, default_render_ref=True)

    for item in sources:
        key = str(item.get("s3_key") or "")
        try:
            data_url = await asyncio.to_thread(
                _fetch_attachment_data_url,
                client,
                bucket,
                key,
                max_bytes,
            )
            render_ref = str(item.get("render_ref") or "").strip()
            source_refs = (render_ref,) if render_ref else ()
            replacements.append(
                _InlineReplacement(
                    source_url=str(item.get("url") or ""),
                    data_url=data_url,
                    source_refs=source_refs,
                )
            )
        except (ClientError, BotoCoreError, ValueError) as exc:
            logger.warning(
                "render_and_contrast: attachment inline failed job_id=%s key=%s err=%s",
                state.get("job_id"),
                key,
                exc,
            )
            errors.append(f"render_and_contrast inline attachment {key}: {exc!s}")

    return replacements, errors


async def _render_one(
    browser: Browser,
    item: SlideItem,
    inline_replacements: list[_InlineReplacement],
) -> tuple[SlideItem, RenderedSlide | None, str | None]:
    fname = item.get("filename") or "slide.html"
    raw_html = item.get("html") or ""
    render_html = _inline_attachment_urls(raw_html, inline_replacements)
    page = await browser.new_page()
    try:
        await page.set_viewport_size(_VIEWPORT)
        await page.route("**/*", _allow_slide_route)
        await page.set_content(enhance_slide_html_for_render(render_html), wait_until="domcontentloaded", timeout=_TIMEOUT_MS)
        try:
            await page.evaluate("() => document.fonts.ready")
        except Exception:
            pass
        try:
            await wait_for_slide_images(page)
        except RuntimeError as exc:
            return ({"filename": fname, "html": raw_html}, None, f"render_and_contrast {fname}: {exc!s}")
        out = await page.evaluate(_CONTRAST_FIX_JS)
        fixed_html = (
            _restore_attachment_urls(await page.content(), inline_replacements)
            if out and out.get("hadViolations")
            else raw_html
        )
        data = await page.screenshot(type="jpeg", quality=_JPEG_QUALITY, full_page=False)
        base = fname.rsplit(".", 1)[0] if "." in fname else fname
        return (
            {"filename": fname, "html": fixed_html},
            {"filename": f"{base}.jpeg", "jpeg_bytes": data},
            None,
        )
    except Exception as exc:  # noqa: BLE001
        return ({"filename": fname, "html": raw_html}, None, f"render_and_contrast {fname}: {exc!s}")
    finally:
        await page.close()


async def render_and_contrast(state: AgentState) -> dict[str, object]:
    logger.info("node=render_and_contrast job_id=%s", state.get("job_id"))
    slides = list(state.get("slides_html") or [])
    errors = copy_errors(state)
    if not slides:
        return {"rendered_slides": [], "errors": errors}
    inline_replacements, inline_errors = await _build_inline_replacements(state)
    errors.extend(inline_errors)
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=["--disable-background-networking", "--disable-extensions", "--no-default-browser-check"]
        )
        try:
            results = await asyncio.gather(*[_render_one(browser, s, inline_replacements) for s in slides])
        finally:
            await browser.close()
    fixed: list[SlideItem] = []
    rendered: list[RenderedSlide] = []
    for slide, image, err in results:
        fixed.append(slide)
        if image:
            rendered.append(image)
        if err:
            logger.error("node=render_and_contrast job_id=%s slide=%s err=%s", state.get("job_id"), slide.get("filename"), err)
            errors.append(err)
    return {"slides_html": fixed, "rendered_slides": rendered, "errors": errors}
