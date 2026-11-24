import httpx
import pytest

from app.openverse import ImageSearchError
from app.stock_selection import select_stock_image


def response(request):
    if request.url.host == "api.openverse.org":
        photo = {"id": "123", "title": "Praia", "creator": "Ana", "license": "cc0",
                 "url": "https://upload.wikimedia.org/wikipedia/a.jpg", "foreign_landing_url": "https://commons.wikimedia.org/a",
                 "license_url": "https://creativecommons.org/publicdomain/zero/1.0/"}
        return httpx.Response(200, json={"results": [photo]})
    return httpx.Response(200, content=b"\xff\xd8\xffimage")


@pytest.mark.asyncio
async def test_selection_keeps_original_credit_and_image_bytes():
    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        selected = await select_stock_image("praia", client=client)
    assert selected.asset_id.startswith("stock_")
    assert selected.content.startswith(b"\xff\xd8\xff")
    assert selected.credit.creator == "Ana"
    assert selected.credit.source_url == "https://commons.wikimedia.org/a"


@pytest.mark.asyncio
async def test_selection_never_reuses_excluded_source():
    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        with pytest.raises(ImageSearchError):
            await select_stock_image("praia", client=client, exclude_sources=frozenset({"https://commons.wikimedia.org/a"}))
