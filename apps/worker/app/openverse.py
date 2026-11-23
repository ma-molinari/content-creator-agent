"""Search Openverse for openly licensed image candidates."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx


_SEARCH_URL = "https://api.openverse.org/v1/images/"
_MAX_IMAGE_BYTES = 5 * 1024 * 1024


class ImageSearchError(Exception):
    """An image search could not be completed."""


@dataclass(frozen=True)
class ImageCandidate:
    id: str
    title: str
    image_url: str
    source_url: str
    creator: str | None
    creator_url: str | None
    license: str
    license_url: str


def _https_url(value: object) -> str | None:
    if not isinstance(value, str) or len(value) > 2048:
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            return None
        if parsed.port not in (None, 443):
            return None
    except ValueError:
        return None
    return value


def _wikimedia_image_url(value: object) -> str | None:
    url = _https_url(value)
    if url is None:
        return None
    parsed = urlsplit(url)
    return url if parsed.hostname == "upload.wikimedia.org" and parsed.path.startswith("/wikipedia/") else None


async def search_images(query: str, *, client: httpx.AsyncClient, limit: int = 10) -> list[ImageCandidate]:
    """Search CC0 candidates; consumers must still verify the original license.

    URLs returned by this function are metadata, not authorization to download.
    Downloads require a separate SSRF-safe network policy.
    """
    query = query.strip()
    if not query or len(query) > 300 or not 1 <= limit <= 20:
        raise ValueError("invalid image search parameters")
    try:
        response = await client.get(_SEARCH_URL, params={"q": query, "license": "cc0", "source": "wikimedia", "page_size": limit},
                                    timeout=10.0, follow_redirects=False)
        response.raise_for_status()
        data = response.json()
        results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(results, list):
            raise ValueError("invalid search response")
        candidates = []
        for item in results[:limit]:
            if not isinstance(item, dict) or item.get("license") != "cc0":
                continue
            image_url = _wikimedia_image_url(item.get("url"))
            source_url = _https_url(item.get("foreign_landing_url"))
            license_url = _https_url(item.get("license_url"))
            identifier = item.get("id")
            if not image_url or not source_url or not license_url or not isinstance(identifier, str) or not identifier:
                continue
            creator = item.get("creator")
            title = item.get("title")
            candidates.append(ImageCandidate(
                id=identifier, title=title if isinstance(title, str) else "",
                image_url=image_url, source_url=source_url,
                creator=creator if isinstance(creator, str) else None,
                creator_url=_https_url(item.get("creator_url")), license="cc0", license_url=license_url,
            ))
        return candidates
    except (httpx.HTTPError, ValueError) as exc:
        raise ImageSearchError("Não foi possível buscar imagens no momento.") from exc


async def download_image(candidate: ImageCandidate, *, client: httpx.AsyncClient) -> bytes:
    """Download a bounded Wikimedia image without following arbitrary URLs."""
    try:
        if _wikimedia_image_url(candidate.image_url) is None:
            raise ValueError("untrusted image URL")
        data = bytearray()
        async with client.stream("GET", candidate.image_url, timeout=15.0, follow_redirects=False) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > _MAX_IMAGE_BYTES:
                    raise ValueError("image too large")
        raw = bytes(data)
        if not (raw.startswith(b"\xff\xd8\xff") or raw.startswith(b"\x89PNG\r\n\x1a\n")
                or (len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP")):
            raise ValueError("invalid image format")
        return raw
    except (httpx.HTTPError, ValueError) as exc:
        raise ImageSearchError("Não foi possível carregar a imagem selecionada.") from exc
