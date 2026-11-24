from unittest.mock import AsyncMock

import httpx
import pytest

from app.post_document_v3 import PostDocumentV3, promote_to_v3
from app.post_document_v2 import PostDocumentV2
from app.stock_pipeline import apply_stock_image
from app.stock_planning import StockPlan
from app.openverse import ImageSearchError
from app.stock_selection import NoSuitableImageError
from tests.test_post_document_v3 import document
from tests.test_stock_selection import choice, response


@pytest.mark.asyncio
async def test_edit_uses_provider_and_preserves_base(monkeypatch):
    base = PostDocumentV3.model_validate(document())
    monkeypatch.setattr("app.stock_pipeline.plan_stock_action", AsyncMock(return_value=StockPlan(action="replace", query="praia", slide_number=1)))
    monkeypatch.setattr("app.stock_selection._choose_photo", AsyncMock(return_value=choice()))
    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        result, assets, fallback = await apply_stock_image(base, request="troque a imagem", mode="edit", authorized_assets={"photo"}, client=client)
    assert not fallback
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
    monkeypatch.setattr("app.stock_selection._choose_photo", AsyncMock(return_value=choice()))
    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        result, assets, fallback = await apply_stock_image(base, request="crie um post", mode="create", authorized_assets=set(), client=client)
    assert not fallback
    assert result.slides[0].background.asset_id in assets
    assert result.credits[result.slides[0].background.asset_id].creator == "Ana"


@pytest.mark.asyncio
async def test_text_edit_does_not_call_provider(monkeypatch):
    base = PostDocumentV3.model_validate(document())
    monkeypatch.setattr("app.stock_pipeline.plan_stock_action", AsyncMock(return_value=StockPlan(action="none", query=None, slide_number=None)))
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("unexpected HTTP"))) as client:
        result, assets, fallback = await apply_stock_image(base, request="edite o texto", mode="edit", authorized_assets={"photo"}, client=client)
    assert not fallback
    assert result == base
    assert assets == {}


@pytest.mark.asyncio
async def test_generic_search_after_no_candidate_keeps_original_relevance(monkeypatch):
    base = PostDocumentV3.model_validate(document())
    select = AsyncMock(side_effect=[NoSuitableImageError("none"), NoSuitableImageError("none")])
    monkeypatch.setattr("app.stock_pipeline.select_stock_image", select)
    plan = StockPlan(action="replace", query="software engineer career", fallback_queries=["developer laptop"], slide_number=1, image_required=False)
    async with httpx.AsyncClient() as client:
        result, assets, fallback = await apply_stock_image(base, request="Crie um post", mode="create", authorized_assets=set(), client=client, plan=plan)
    assert fallback and result == base and assets == {}
    assert [call.args[0] for call in select.await_args_list] == ["software engineer career", "developer laptop"]
    assert select.await_args_list[1].kwargs["relevance_query"] == "software engineer career"


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,required", [("create", True), ("edit", False)])
async def test_required_image_or_edit_does_not_publish_partial_version(monkeypatch, mode, required):
    base = PostDocumentV3.model_validate(document())
    before = base.model_dump_json()
    monkeypatch.setattr("app.stock_pipeline.select_stock_image", AsyncMock(side_effect=NoSuitableImageError("none")))
    plan = StockPlan(action="replace", query="praia", fallback_queries=["nature"], slide_number=1, image_required=required)
    async with httpx.AsyncClient() as client:
        with pytest.raises(NoSuitableImageError, match="outro termo"):
            await apply_stock_image(base, request="troque a foto", mode=mode, authorized_assets={"photo"}, client=client, plan=plan)
    assert base.model_dump_json() == before


@pytest.mark.asyncio
async def test_optional_creation_falls_back_on_provider_failure(monkeypatch):
    base = PostDocumentV3.model_validate(document())
    select = AsyncMock(side_effect=ImageSearchError("unavailable"))
    monkeypatch.setattr("app.stock_pipeline.select_stock_image", select)
    plan = StockPlan(action="replace", query="praia", fallback_queries=["nature"], slide_number=1, image_required=False)
    async with httpx.AsyncClient() as client:
        result, assets, fallback = await apply_stock_image(base, request="crie", mode="create", authorized_assets=set(), client=client, plan=plan)
    assert fallback and result == base and assets == {}
    assert select.await_count == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,required", [("create", True), ("edit", False)])
async def test_provider_failure_does_not_publish_required_image_or_edit(monkeypatch, mode, required):
    base = PostDocumentV3.model_validate(document())
    monkeypatch.setattr("app.stock_pipeline.select_stock_image", AsyncMock(side_effect=ImageSearchError("unavailable")))
    plan = StockPlan(action="replace", query="praia", slide_number=1, image_required=required)
    async with httpx.AsyncClient() as client:
        with pytest.raises(ImageSearchError, match="unavailable"):
            await apply_stock_image(base, request="crie", mode=mode, authorized_assets={"photo"}, client=client, plan=plan)
    assert base.slides[0].background.asset_id == "photo"
