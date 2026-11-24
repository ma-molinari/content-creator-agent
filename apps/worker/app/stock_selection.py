"""Select an Openverse result and retain provenance alongside its bytes."""

from dataclasses import dataclass
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup

from app.openverse import ImageSearchError, download_image, search_images
from app.post_document_v3 import ImageCreditV3


@dataclass(frozen=True)
class SelectedStockImage:
    asset_id: str
    content: bytes
    credit: ImageCreditV3


def _plain_credit(value: str | None) -> str:
    if not value:
        return ""
    if "<" not in value or ">" not in value:
        return " ".join(value.split())[:500]
    document = BeautifulSoup(value, "html.parser")
    for node in document.select("script, style, [hidden]"):
        node.decompose()
    for node in document.find_all(style=True):
        normalized = "".join(node.get("style", "").lower().split())
        if "display:none" in normalized or "visibility:hidden" in normalized:
            node.decompose()
    return " ".join(document.stripped_strings)[:500]


async def select_stock_image(query: str, *, client: httpx.AsyncClient,
                             exclude_sources: frozenset[str] = frozenset()) -> SelectedStockImage:
    candidates = await search_images(query, client=client)
    for candidate in candidates:
        if candidate.source_url in exclude_sources:
            continue
        try:
            content = await download_image(candidate, client=client)
            creator = _plain_credit(candidate.creator)
            credit = ImageCreditV3.model_validate({
                "title": _plain_credit(candidate.title), "creator": creator or None,
                "sourceUrl": candidate.source_url, "license": candidate.license, "licenseUrl": candidate.license_url,
            })
            return SelectedStockImage(asset_id="stock_" + uuid4().hex, content=content, credit=credit)
        except (ImageSearchError, ValueError):
            continue
    raise ImageSearchError("Não foi encontrada uma imagem disponível para esse tema.")
