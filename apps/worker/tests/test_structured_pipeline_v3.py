from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from app.post_document_v2 import PostDocumentV2
from app.post_document_v3 import PostDocumentV3
from app.stock_planning import StockPlan
from tests.test_post_document_v3 import document as v3_document
from tests.test_stock_selection import response as provider_response


@pytest.mark.asyncio
async def test_v3_create_connects_provider_and_publishes_credit(monkeypatch):
    from app.nodes import structured_pipeline_v3 as module
    settings = SimpleNamespace(aws_region="us-east-1", aws_access_key_id="test", aws_secret_access_key="test",
                               aws_s3_bucket="test", go_api_url="http://api", worker_api_key="test")
    data = v3_document()
    data["schemaVersion"] = 2
    data.pop("credits")
    data["slides"][0]["background"] = {"type": "solid", "color": {"token": "background"}}
    base = PostDocumentV2.model_validate(data)
    monkeypatch.setattr(module, "get_settings", lambda: settings)
    monkeypatch.setattr(module.boto3, "client", lambda *a, **k: object())
    monkeypatch.setattr(module, "report_job_progress", AsyncMock())
    monkeypatch.setattr(module, "attachment_analyze", AsyncMock(return_value={}))
    monkeypatch.setattr(module, "generate_structured_post_v2", AsyncMock(return_value=base))
    monkeypatch.setattr(module, "plan_stock_action", AsyncMock(return_value=StockPlan(action="replace", query="praia", slide_number=1)))
    actual_client = httpx.AsyncClient
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda: actual_client(transport=httpx.MockTransport(provider_response)))
    copy = AsyncMock(return_value=SimpleNamespace(contents={"x": b"image"}))
    monkeypatch.setattr(module, "copy_version_assets", copy)
    monkeypatch.setattr(module, "render_structured_post", AsyncMock(return_value=([{}], [{}])))
    monkeypatch.setattr(module, "upload_structured_post", AsyncMock(return_value=object()))
    complete = AsyncMock(return_value=204)
    monkeypatch.setattr(module, "send_structured_completion", complete)
    state = {"job_id": str(uuid4()), "generation_mode": "create", "raw_message": "Crie um post", "chat_post_type": "single"}
    assert await module.structured_pipeline_v3(state) == {}
    published = copy.await_args.args[0]
    assert isinstance(published, PostDocumentV3)
    assert published.slides[0].background.type == "image"
    assert copy.await_args.kwargs["selected_assets"]
    assert "commons.wikimedia.org/a" in complete.await_args.kwargs["assistant_text"]
    assert complete.await_args.kwargs["schema_version"] == 3


@pytest.mark.asyncio
async def test_v3_edit_preserves_previous_snapshot_and_uses_new_asset(monkeypatch):
    from app.nodes import structured_pipeline_v3 as module
    settings = SimpleNamespace(aws_region="us-east-1", aws_access_key_id="test", aws_secret_access_key="test",
                               aws_s3_bucket="test", go_api_url="http://api", worker_api_key="test")
    original = PostDocumentV3.model_validate(v3_document())
    monkeypatch.setattr(module, "get_settings", lambda: settings)
    monkeypatch.setattr(module.boto3, "client", lambda *a, **k: object())
    monkeypatch.setattr(module, "fetch_bytes_limited", lambda *a: original.model_dump_json(by_alias=True).encode())
    monkeypatch.setattr(module, "report_job_progress", AsyncMock())
    monkeypatch.setattr(module, "attachment_analyze", AsyncMock(return_value={}))
    monkeypatch.setattr(module, "plan_stock_action", AsyncMock(return_value=StockPlan(action="replace", query="praia", slide_number=1)))
    monkeypatch.setattr(module, "plan_content_edit_v3", AsyncMock(return_value=original))
    actual_client = httpx.AsyncClient
    monkeypatch.setattr(module.httpx, "AsyncClient", lambda: actual_client(transport=httpx.MockTransport(provider_response)))
    copy = AsyncMock(return_value=SimpleNamespace(contents={"x": b"image"}))
    monkeypatch.setattr(module, "copy_version_assets", copy)
    monkeypatch.setattr(module, "render_structured_post", AsyncMock(return_value=([{}], [{}])))
    monkeypatch.setattr(module, "upload_structured_post", AsyncMock(return_value=object()))
    monkeypatch.setattr(module, "send_structured_completion", AsyncMock(return_value=204))
    state = {"job_id": str(uuid4()), "generation_mode": "edit", "raw_message": "Troque a foto", "chat_post_type": "single",
             "document_s3_key": f"slides/{uuid4()}/document.json", "authorized_asset_sources": {"photo": "slides/old/assets/photo.jpg"}}
    assert await module.structured_pipeline_v3(state) == {}
    published = copy.await_args.args[0]
    assert original.slides[0].background.asset_id == "photo"
    assert published.slides[0].background.asset_id != "photo"
    assert published.slides[0].background.asset_id in copy.await_args.kwargs["selected_assets"]
    assert "photo" not in published.credits
