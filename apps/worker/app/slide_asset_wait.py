"""Wait for slide image assets before JPEG capture."""

from __future__ import annotations

import asyncio
from typing import Any, Mapping, Protocol, cast


class _PageLike(Protocol):
    async def evaluate(self, expression: str, arg: object = ...) -> object:
        ...


_WAIT_FOR_SLIDE_IMAGES_JS = """
async (timeoutMs) => {
  const timeout = Number.isFinite(timeoutMs) && timeoutMs > 0 ? timeoutMs : 10000;

  function cssUrls(value) {
    const out = [];
    const re = /url\\((['"]?)(.*?)\\1\\)/gi;
    let match;
    while ((match = re.exec(String(value || '')))) {
      const url = (match[2] || '').trim();
      if (url && !url.startsWith('data:')) out.push(url);
    }
    return out;
  }

  function unique(values) {
    return Array.from(new Set(values.filter(Boolean)));
  }

  async function waitForElementImage(img, index) {
    const src = img.currentSrc || img.src || '';
    if (!src) return null;
    if (img.complete) {
      if (img.naturalWidth > 0) {
        if (img.decode) {
          try {
            await img.decode();
          } catch (_) {
            /* Some formats/browsers reject decode after successful load; paint is still available. */
          }
        }
        return null;
      }
      return { kind: 'img', index, url: src, reason: 'failed' };
    }
    return await new Promise((resolve) => {
      const cleanup = () => {
        img.removeEventListener('load', onLoad);
        img.removeEventListener('error', onError);
      };
      const onLoad = async () => {
        cleanup();
        if (img.decode) {
          try {
            await img.decode();
          } catch (_) {
            /* See note above. */
          }
        }
        resolve(null);
      };
      const onError = () => {
        cleanup();
        resolve({ kind: 'img', index, url: src, reason: 'failed' });
      };
      img.addEventListener('load', onLoad, { once: true });
      img.addEventListener('error', onError, { once: true });
    });
  }

  async function waitForCssImage(url, index) {
    return await new Promise((resolve) => {
      const image = new Image();
      image.onload = async () => {
        if (image.decode) {
          try {
            await image.decode();
          } catch (_) {
            /* Loaded background images are still paintable even if decode rejects. */
          }
        }
        resolve(null);
      };
      image.onerror = () => resolve({ kind: 'background-image', index, url, reason: 'failed' });
      image.src = url;
    });
  }

  const elementImages = Array.from(document.images || []);
  const cssImageUrls = unique(
    Array.from(document.querySelectorAll('*')).flatMap((el) =>
      cssUrls(getComputedStyle(el).backgroundImage)
    )
  );
  const waits = [
    ...elementImages.map((img, index) => waitForElementImage(img, index)),
    ...cssImageUrls.map((url, index) => waitForCssImage(url, index)),
  ];

  const timedOut = Symbol('timedOut');
  const result = await Promise.race([
    Promise.all(waits),
    new Promise((resolve) => setTimeout(() => resolve(timedOut), timeout)),
  ]);

  if (result === timedOut) {
    return {
      ok: false,
      timedOut: true,
      total: waits.length,
      failed: [],
    };
  }

  const failed = result.filter(Boolean);
  return {
    ok: failed.length === 0,
    timedOut: false,
    total: waits.length,
    failed,
  };
}
"""


def _summarize_wait_result(result: Mapping[str, Any], *, timeout_ms: int) -> str | None:
    if result.get("ok"):
        return None
    total = int(result.get("total") or 0)
    if result.get("timedOut"):
        return f"timed out after {timeout_ms}ms waiting for {total} slide image asset(s)"

    failed = result.get("failed") or []
    if not failed:
        return f"failed waiting for {total} slide image asset(s)"

    pieces: list[str] = []
    for item in list(failed)[:3]:
        if not isinstance(item, Mapping):
            continue
        kind = str(item.get("kind") or "image")
        url = str(item.get("url") or "")
        snip = url[:160] + ("..." if len(url) > 160 else "")
        pieces.append(f"{kind} {snip}".strip())
    suffix = "" if len(failed) <= 3 else f" (+{len(failed) - 3} more)"
    detail = "; ".join(pieces) if pieces else f"{len(failed)} failed asset(s)"
    return f"failed loading slide image asset(s): {detail}{suffix}"


async def wait_for_slide_images(page: _PageLike, *, timeout_ms: int = 10_000) -> None:
    """Wait until HTML and CSS image assets are loaded/decoded or raise RuntimeError."""
    try:
        raw = await asyncio.wait_for(
            page.evaluate(_WAIT_FOR_SLIDE_IMAGES_JS, timeout_ms),
            timeout=(timeout_ms / 1000) + 1,
        )
    except asyncio.TimeoutError as exc:
        raise RuntimeError(
            f"timed out after {timeout_ms}ms waiting for slide image asset(s)"
        ) from exc

    result = cast(Mapping[str, Any], raw or {})
    message = _summarize_wait_result(result, timeout_ms=timeout_ms)
    if message:
        raise RuntimeError(message)
