"""V2 dispatch and immutable persistence stay isolated from V1."""

import asyncio
import io
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks, HTTPException
from pydantic import ValidationError

from app.graph import build_graph
from app.job_payload import DispatchPayload, initial_state
from app.main import post_structured_jobs, post_structured_jobs_v2
from app.post_document import PostDocumentV1
from app.post_operations_v2 import apply_operations_v2
from app.post_document_v2 import promote_v1
from app.immutable_assets import CopiedAssets
from app.nodes.structured_pipeline import structured_pipeline
from app.structured_upload import StructuredCallbackUnknown, StructuredUpload


class MemoryS3:
    def __init__(self): self.objects = {}
    def put_object(self, *, Bucket, Key, Body, ContentType, IfNoneMatch):
        assert IfNoneMatch == "*" and Key not in self.objects
        self.objects[Key] = (bytes(Body), ContentType)
    def get_object(self, *, Bucket, Key):
        data, content_type = self.objects[Key]
        return {"Body": io.BytesIO(data), "ContentType": content_type}
    def head_object(self, *, Bucket, Key):
        assert Key in self.objects
        return {}


def test_routes_require_explicit_target_and_preserve_v1(monkeypatch):
    monkeypatch.setattr("app.config.get_settings", lambda: SimpleNamespace(worker_api_key="secret"))
    base = dict(job_id=uuid4(), user_id=uuid4(), chat_id=uuid4(), post_format="structured_v1", generation_mode="create")
    v2 = DispatchPayload(**base, target_schema_version=2)
    with pytest.raises(HTTPException):
        asyncio.run(post_structured_jobs(v2, BackgroundTasks(), "secret"))
    assert asyncio.run(post_structured_jobs_v2(v2, BackgroundTasks(), "secret"))["accepted"]
    with pytest.raises(HTTPException):
        asyncio.run(post_structured_jobs_v2(DispatchPayload(**base), BackgroundTasks(), "secret"))
    with pytest.raises(ValidationError):
        DispatchPayload(**base, target_schema_version=True)
    with pytest.raises(ValidationError):
        DispatchPayload(**dict(base, generation_mode="edit"), target_schema_version=2)


def test_v1_to_v2_edit_keeps_original_and_inherited_asset_without_reference_fetch(monkeypatch):
    s3 = MemoryS3()
    old_job, new_job, user, chat = uuid4(), uuid4(), uuid4(), uuid4()
    source = f"slides/{old_job}/assets/asset1.png"
    image = b"\x89PNG\r\n\x1a\nimage-content"
    s3.objects[source] = (image, "image/png")
    base = PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{
        "id": "s", "layout": "hero", "background": {"type": "solid", "color": "#000000"},
        "elements": [{"id": "t", "type": "text", "role": "heading", "content": "Original", "style": {"color": "#FFFFFF", "size": "large"}},
                     {"id": "i", "type": "image", "assetId": "asset1", "fit": "cover"}]}]})
    key = f"slides/{old_job}/document.json"
    old_bytes = base.model_dump_json(by_alias=True).encode()
    s3.objects[key] = (old_bytes, "application/json")
    settings = SimpleNamespace(aws_region="test", aws_access_key_id="test", aws_secret_access_key="test", aws_s3_bucket="bucket", go_api_url="http://api", worker_api_key="key")
    monkeypatch.setattr("app.nodes.structured_pipeline.get_settings", lambda: settings)
    monkeypatch.setattr("app.nodes.structured_pipeline.boto3.client", lambda *a, **kw: s3)
    monkeypatch.setattr("app.nodes.structured_pipeline.report_job_progress", AsyncMock())
    monkeypatch.setattr("app.graph.report_job_progress", AsyncMock())
    monkeypatch.setattr("app.nodes.structured_pipeline.attachment_analyze", AsyncMock(return_value={}))
    monkeypatch.setattr("app.nodes.structured_pipeline.requests_reference_reapplication", AsyncMock(return_value=False))
    extract = AsyncMock(side_effect=AssertionError("references must not be fetched"))
    monkeypatch.setattr("app.nodes.structured_pipeline.extract_visual_direction", extract)
    monkeypatch.setattr("app.nodes.profile_overview.describe_references", extract)
    async def edit(**kwargs):
        assert not kwargs["reapply_references"] and kwargs["visual_direction"] is None
        return apply_operations_v2(kwargs["document"], [{"op": "set_text", "slideId": "s", "elementId": "t", "content": "Editado"}], kwargs["authorized_assets"])
    monkeypatch.setattr("app.nodes.structured_pipeline.plan_structured_edit_v2", edit)
    monkeypatch.setattr("app.nodes.structured_pipeline.render_structured_post", AsyncMock(return_value=([{"filename": "slide_01.html", "html": "<html></html>"}], [{"filename": "slide_01.jpeg", "jpeg_bytes": b"\xff\xd8\xffjpeg"}])))
    callback = AsyncMock(return_value=SimpleNamespace(status_code=204))
    monkeypatch.setattr("app.structured_upload.post_complete_callback", callback)
    payload = DispatchPayload(job_id=new_job, user_id=user, chat_id=chat, post_format="structured_v1", target_schema_version=2,
        generation_mode="edit", base_version_id=uuid4(), document_s3_key=key, chat_post_type="single",
        authorized_asset_sources={"asset1": source}, reference_s3_keys=["unavailable-reference"], reference_asset_sources={"ref": "unavailable-reference"})
    asyncio.run(build_graph().ainvoke(initial_state(payload)))
    new_prefix = f"slides/{new_job}/"
    result = json.loads(s3.objects[new_prefix + "document.json"][0])
    manifest = json.loads(s3.objects[new_prefix + "assets.json"][0])
    assert result["schemaVersion"] == 2 and result["slides"][0]["elements"][0]["content"] == "Editado"
    assert s3.objects[key][0] == old_bytes and s3.objects[manifest["asset1"]][0] == image
    assert callback.await_args.kwargs["json_body"]["structured"]["schemaVersion"] == 2
    assert callback.await_args.kwargs["json_body"]["structured"]["rendererVersion"] == "2.0.0"
    assert extract.await_count == 0


def test_create_uses_references_and_unknown_callback_is_not_failed(monkeypatch):
    base = PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{
        "id": "s", "layout": "hero", "background": {"type": "solid", "color": "#000000"},
        "elements": [{"id": "t", "type": "text", "role": "heading", "content": "Oi", "style": {"color": "#FFFFFF", "size": "large"}}]}]})
    doc = promote_v1(base)
    mod = "app.nodes.structured_pipeline."
    settings = SimpleNamespace(aws_region="test", aws_access_key_id="test", aws_secret_access_key="test", aws_s3_bucket="bucket", go_api_url="http://api", worker_api_key="key")
    monkeypatch.setattr(mod + "get_settings", lambda: settings)
    monkeypatch.setattr(mod + "boto3.client", lambda *args, **kwargs: object())
    monkeypatch.setattr(mod + "report_job_progress", AsyncMock())
    monkeypatch.setattr(mod + "attachment_analyze", AsyncMock(return_value={}))
    direction = object()
    extract = AsyncMock(return_value=direction)
    generate = AsyncMock(return_value=doc)
    monkeypatch.setattr(mod + "extract_visual_direction", extract)
    monkeypatch.setattr(mod + "generate_structured_post_v2", generate)
    monkeypatch.setattr(mod + "copy_version_assets", AsyncMock(return_value=CopiedAssets({}, {})))
    monkeypatch.setattr(mod + "render_structured_post", AsyncMock(return_value=([{"filename": "slide_01.html", "html": "html"}], [{"filename": "slide_01.jpeg", "jpeg_bytes": b"\xff\xd8\xff"}])))
    monkeypatch.setattr(mod + "upload_structured_post", AsyncMock(return_value=StructuredUpload("slides/key/document.json", [])))
    monkeypatch.setattr(mod + "send_structured_completion", AsyncMock(side_effect=StructuredCallbackUnknown("unknown")))
    payload = DispatchPayload(job_id=uuid4(), user_id=uuid4(), chat_id=uuid4(), post_format="structured_v1", target_schema_version=2,
                              generation_mode="create", chat_post_type="single", reference_s3_keys=["reference"], reference_asset_sources={"ref": "reference"})
    with pytest.raises(StructuredCallbackUnknown):
        asyncio.run(structured_pipeline(initial_state(payload)))
    assert extract.await_args.kwargs["reference_keys"] == ["reference"]
    assert generate.await_args.kwargs["visual_direction"] is direction
