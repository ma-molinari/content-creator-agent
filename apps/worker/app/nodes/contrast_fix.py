"""Fix low-contrast text in slide HTML using Playwright computed styles."""

from __future__ import annotations

import asyncio
import logging

from playwright.async_api import Browser, Route, async_playwright

from app.slide_render_html import enhance_slide_html_for_render
from app.state import AgentState, SlideItem, copy_errors

logger = logging.getLogger(__name__)

_TIMEOUT_MS = 60_000

_CONTRAST_FIX_JS = """
() => {
  const STYLE_ID = '__pipeline_contrast_fix';
  function parseRgb(s) {
    const m = String(s).match(/rgba?\\s*\\(\\s*(\\d+)\\s*,\\s*(\\d+)\\s*,\\s*(\\d+)(?:\\s*,\\s*([0-9.]+))?\\s*\\)/i);
    if (!m) return null;
    const r = +m[1];
    const g = +m[2];
    const b = +m[3];
    if (m[4] !== undefined && parseFloat(m[4]) < 0.99) return null;
    return { r, g, b };
  }
  function relLum(r, g, b) {
    const lin = (c) => {
      c /= 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  }
  function contrastRatio(l1, l2) {
    const hi = Math.max(l1, l2);
    const lo = Math.min(l1, l2);
    return (hi + 0.05) / (lo + 0.05);
  }
  function effectiveBgRgb(el) {
    let cur = el;
    while (cur && cur !== document.documentElement) {
      const bg = getComputedStyle(cur).backgroundColor;
      const parsed = parseRgb(bg);
      if (parsed) return parsed;
      cur = cur.parentElement;
    }
    return { r: 255, g: 255, b: 255 };
  }
  function threshold(fs, bold) {
    if (fs >= 24) return 3.0;
    if (bold && fs >= 18.67) return 3.0;
    return 4.5;
  }
  function fontSizePx(el) {
    const fs = getComputedStyle(el).fontSize;
    const m = fs.match(/([0-9.]+)px/);
    return m ? parseFloat(m[1]) : 16;
  }
  function isBold(el) {
    const w = getComputedStyle(el).fontWeight;
    if (w === 'bold' || w === 'bolder') return true;
    const n = parseInt(w, 10);
    return !Number.isNaN(n) && n >= 600;
  }
  if (!document.body) {
    return { hadViolations: false };
  }
  const seen = new WeakSet();
  let hadViolations = false;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) {
    if (!node.textContent || !/\\S/.test(node.textContent)) continue;
    const el = node.parentElement;
    if (!el || seen.has(el)) continue;
    const st = getComputedStyle(el);
    if (st.visibility === 'hidden' || st.display === 'none' || parseFloat(st.opacity) === 0) {
      continue;
    }
    if (el.getClientRects().length === 0) continue;
    seen.add(el);
    const fg = parseRgb(st.color);
    if (!fg) continue;
    const bgRgb = effectiveBgRgb(el);
    const fgL = relLum(fg.r, fg.g, fg.b);
    const bgL = relLum(bgRgb.r, bgRgb.g, bgRgb.b);
    const ratio = contrastRatio(fgL, bgL);
    const thr = threshold(fontSizePx(el), isBold(el));
    /* Use tiny epsilon so float noise does not false-positive. */
    if (ratio >= thr - 1e-6) continue;
    hadViolations = true;
    const bgDark = bgL < 0.5;
    el.setAttribute('data-cf', bgDark ? '1' : '2');
  }
  if (hadViolations && !document.getElementById(STYLE_ID)) {
    const s = document.createElement('style');
    s.id = STYLE_ID;
    s.textContent =
      'body *[data-cf="1"]{color:#e2e8f0!important;}' +
      'body *[data-cf="2"]{color:#1e293b!important;}';
    document.head.appendChild(s);
  }
  return { hadViolations };
}
"""


async def _allow_slide_route(route: Route) -> None:
    """Block remote assets except Google Fonts (matches render_to_jpeg)."""
    url = route.request.url
    if url.startswith("data:"):
        await route.continue_()
        return
    if "fonts.googleapis.com" in url or "fonts.gstatic.com" in url:
        await route.continue_()
        return
    await route.abort()


async def _fix_one_slide(browser: Browser, item: SlideItem) -> tuple[SlideItem, str | None]:
    fname = item.get("filename") or "slide.html"
    raw_html = item.get("html") or ""
    html = enhance_slide_html_for_render(raw_html)
    page = await browser.new_page()
    try:
        await page.set_viewport_size({"width": 1080, "height": 1350})
        await page.route("**/*", _allow_slide_route)
        await page.set_content(html, wait_until="domcontentloaded", timeout=_TIMEOUT_MS)
        try:
            await page.evaluate("() => document.fonts.ready")
        except Exception as exc:
            logger.debug("contrast_fix: document.fonts.ready skipped (%s)", exc)
        out = await page.evaluate(_CONTRAST_FIX_JS)
        had = bool(out and out.get("hadViolations"))
        if not had:
            return ({"filename": fname, "html": raw_html}, None)
        fixed_html = await page.content()
        return ({"filename": fname, "html": fixed_html}, None)
    except Exception as exc:  # noqa: BLE001 — capture Playwright errors per slide
        return ({"filename": fname, "html": raw_html}, f"contrast_fix {fname}: {exc!s}")
    finally:
        await page.close()


async def contrast_fix(state: AgentState) -> dict:
    logger.info("node=contrast_fix job_id=%s", state.get("job_id"))
    slides = state.get("slides_html") or []
    errors = copy_errors(state)
    if not slides:
        return {"slides_html": [], "errors": errors}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            args=[
                "--disable-background-networking",
                "--disable-extensions",
                "--no-default-browser-check",
            ]
        )
        try:
            results = await asyncio.gather(*[_fix_one_slide(browser, item) for item in slides])
        finally:
            await browser.close()

    fixed_slides: list[SlideItem] = []
    for slide_out, err in results:
        fixed_slides.append(slide_out)
        if err:
            errors.append(err)

    return {"slides_html": fixed_slides, "errors": errors}
