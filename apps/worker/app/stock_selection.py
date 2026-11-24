"""Select an Openverse result and retain provenance alongside its bytes."""

from dataclasses import dataclass
from uuid import uuid4

import httpx

from app.openverse import ImageSearchError, download_image, search_images
from app.post_document_v3 import ImageCreditV3


@dataclass(frozen=True)
class SelectedStockImage:
    asset_id: str
    content: bytes
    credit: ImageCreditV3


async def select_stock_image(query: str, *, client: httpx.AsyncClient,
                             exclude_sources: frozenset[str] = frozenset()) -> SelectedStockImage:
    candidates = await search_images(query, client=client)
    for candidate in candidates:
        if candidate.source_url in exclude_sources:
            continue
        try:
            content = await download_image(candidate, client=client)
            credit = ImageCreditV3.model_validate({
                "title": candidate.title[:500], "creator": candidate.creator[:500] if candidate.creator else None,
                "sourceUrl": candidate.source_url, "license": candidate.license, "licenseUrl": candidate.license_url,
            })
            return SelectedStockImage(asset_id="stock_" + uuid4().hex, content=content, credit=credit)
        except (ImageSearchError, ValueError):
            continue
    raise ImageSearchError("Não foi encontrada uma imagem disponível para esse tema.")
