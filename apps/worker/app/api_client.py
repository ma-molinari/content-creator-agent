"""HTTP callbacks to Go API with retries for transient failures."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Mapping

import httpx

logger = logging.getLogger(__name__)

DEFAULT_ATTEMPTS = 5
DEFAULT_BACKOFF_INITIAL = 0.5


def _transport_retryable(exc: BaseException) -> bool:
    return isinstance(
        exc,
        (
            httpx.ConnectError,
            httpx.ReadTimeout,
            httpx.ConnectTimeout,
        ),
    )


async def post_complete_callback(
    url: str,
    *,
    json_body: Mapping[str, Any] | None,
    headers: Mapping[str, str] | None,
    timeout: float = 30.0,
    attempts: int = DEFAULT_ATTEMPTS,
    backoff_initial: float = DEFAULT_BACKOFF_INITIAL,
) -> httpx.Response:
    """POST JSON to the job complete endpoint; retries transport errors and 5xx."""
    attempts = max(1, attempts)
    hdr = dict(headers) if headers else None
    payload = dict(json_body) if json_body is not None else None

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(attempts):
            try:
                response = await client.post(url, json=payload, headers=hdr)
            except Exception as exc:
                if not _transport_retryable(exc):
                    raise
                if attempt >= attempts - 1:
                    logger.error(
                        "complete callback transport failed after %d attempts url=%s",
                        attempts,
                        url,
                        exc_info=exc,
                    )
                    raise
                delay = backoff_initial * (2**attempt)
                logger.warning(
                    "complete callback transport error attempt=%d/%d url=%s retry_in=%.2fs err=%s",
                    attempt + 1,
                    attempts,
                    url,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
                continue

            if response.status_code >= 500:
                if attempt >= attempts - 1:
                    return response
                delay = backoff_initial * (2**attempt)
                logger.warning(
                    "complete callback 5xx attempt=%d/%d url=%s status=%d retry_in=%.2fs",
                    attempt + 1,
                    attempts,
                    url,
                    response.status_code,
                    delay,
                )
                await asyncio.sleep(delay)
                continue

            return response
