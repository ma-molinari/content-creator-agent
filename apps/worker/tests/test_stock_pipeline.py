from unittest.mock import AsyncMock

import httpx
import pytest

from app.post_document_v3 import PostDocumentV3, promote_to_v3
from app.post_document_v2 import PostDocumentV2
from app.stock_pipeline import apply_stock_image
from app.stock_planning import StockPlan
from tests.test_post_document_v3 import document
from tests.test_stock_selection import response


@pytest.mark.asyncio
async def test_edit_uses_provider_and_preserves_base(monkeypatch):
    base = PostDocumentV3.model_validate(document())
    monkeypatch.setattr("app.stock_pipeline.plan_stock_action", AsyncMock(return_value=StockPlan(action="replace", query="praia", slide_number=1)))
    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        result, assets = await apply_stock_image(base, request="troque a imagem", mode="edit", authorized_assets={"photo"}, client=client)
    asset_id = result.slides[0].background.asset_id
    assert asset_id in assets
    assert result.credits[asset_id].source_url == "https://commons.wikimedia.org/a"
    assert base.slides[0].background.asset_id == "photo"
    assert base.credits["photo"].title == "Paisagem"


@pytest.mark.asyncio
async def test_create_promotes_v2_and_selects_photo(monkeypatch):
    data = document()
    data["schemaVersion"] = 2
    data.pop("credits")
    data["slides"][0]["background"] = {"type": "solid", "color": {"token": "background"}}
    base = promote_to_v3(PostDocumentV2.model_validate(data))
    monkeypatch.setattr("app.stock_pipeline.plan_stock_action", AsyncMock(return_value=StockPlan(action="replace", query="praia", slide_number=1)))
    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        result, assets = await apply_stock_image(base, request="crie um post", mode="create", authorized_assets=set(), client=client)
    assert result.slides[0].background.asset_id in assets
    assert result.credits[result.slides[0].background.asset_id].creator == "Ana"


@pytest.mark.asyncio
async def test_text_edit_does_not_call_provider(monkeypatch):
    base = PostDocumentV3.model_validate(document())
    monkeypatch.setattr("app.stock_pipeline.plan_stock_action", AsyncMock(return_value=StockPlan(action="none", query=None, slide_number=None)))
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("unexpected HTTP"))) as client:
        result, assets = await apply_stock_image(base, request="edite o texto", mode="edit", authorized_assets={"photo"}, client=client)
    assert result == base
    assert assets == {}
