"""Exercise actual immutable asset and snapshot persistence without external services."""

import asyncio
import io
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.job_payload import DispatchPayload, initial_state
from app.graph import build_graph
from app.post_document import PostDocumentV1
from app.post_operations import apply_operations


class MemoryS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, *, Bucket, Key, Body, ContentType, IfNoneMatch):
        assert IfNoneMatch == "*"
        assert Key not in self.objects
        self.objects[Key] = (bytes(Body), ContentType)

    def get_object(self, *, Bucket, Key):
        data, content_type = self.objects[Key]
        return {"Body": io.BytesIO(data), "ContentType": content_type}

    def head_object(self, *, Bucket, Key):
        assert Key in self.objects
        return {}


def test_create_then_edit_preserves_snapshot_and_inherited_asset(monkeypatch):
    s3 = MemoryS3()
    image = b"\x89PNG\r\n\x1a\nimage-content"
    source = "users/owned/reference.png"
    s3.objects[source] = (image, "image/png")
    doc = PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{
        "id": "s", "layout": "hero", "background": {"type": "solid", "color": "#000000"},
        "elements": [
            {"id": "title", "type": "text", "role": "heading", "content": "Original", "style": {"color": "#ffffff", "size": "large"}},
            {"id": "image", "type": "image", "assetId": "asset1", "fit": "cover"},
        ],
    }]})
    settings = SimpleNamespace(aws_region="test", aws_access_key_id="test", aws_secret_access_key="test", aws_s3_bucket="bucket", go_api_url="http://api", worker_api_key="key")
    monkeypatch.setattr("app.nodes.structured_pipeline.get_settings", lambda: settings)
    monkeypatch.setattr("app.nodes.structured_pipeline.boto3.client", lambda *a, **kw: s3)
    monkeypatch.setattr("app.nodes.structured_pipeline.report_job_progress", AsyncMock())
    monkeypatch.setattr("app.graph.report_job_progress", AsyncMock())
    monkeypatch.setattr("app.nodes.structured_pipeline.attachment_analyze", AsyncMock(return_value={}))
    monkeypatch.setattr("app.nodes.structured_pipeline.generate_structured_post", AsyncMock(return_value=doc))

    async def edit(**kwargs):
        return apply_operations(kwargs["document"], [{"op": "set_text", "slideId": "s", "elementId": "title", "content": "Editado"}], kwargs["authorized_assets"])

    monkeypatch.setattr("app.nodes.structured_pipeline.plan_structured_edit", edit)
    monkeypatch.setattr("app.nodes.structured_pipeline.render_structured_post", AsyncMock(return_value=([{"filename": "slide_01.html", "html": "<html></html>"}], [{"filename": "slide_01.jpeg", "jpeg_bytes": b"\xff\xd8\xffjpeg"}])))
    callback = AsyncMock(return_value=SimpleNamespace(status_code=204))
    monkeypatch.setattr("app.structured_upload.post_complete_callback", callback)
    user, chat, create_job, edit_job = uuid4(), uuid4(), uuid4(), uuid4()
    create = DispatchPayload(job_id=create_job, user_id=user, chat_id=chat, post_format="structured_v1", generation_mode="create", chat_post_type="single", authorized_asset_sources={"asset1": source})
    graph = build_graph()
    asyncio.run(graph.ainvoke(initial_state(create)))
    first_prefix = f"slides/{create_job}/"
    first_document = s3.objects[first_prefix + "document.json"][0]
    manifest = json.loads(s3.objects[first_prefix + "assets.json"][0])
    assert s3.objects[manifest["asset1"]][0] == image
    del s3.objects[source]
    edit_payload = DispatchPayload(job_id=edit_job, user_id=user, chat_id=chat, post_format="structured_v1", generation_mode="edit", base_version_id=uuid4(), document_s3_key=first_prefix + "document.json", chat_post_type="single", authorized_asset_sources=manifest)
    asyncio.run(graph.ainvoke(initial_state(edit_payload)))
    second_prefix = f"slides/{edit_job}/"
    second_document = s3.objects[second_prefix + "document.json"][0]
    second_manifest = json.loads(s3.objects[second_prefix + "assets.json"][0])
    assert s3.objects[first_prefix + "document.json"][0] == first_document
    assert s3.objects[second_manifest["asset1"]][0] == image
    assert second_manifest["asset1"] != manifest["asset1"]
    assert json.loads(first_document)["slides"][0]["elements"][0]["content"] == "Original"
    assert json.loads(second_document)["slides"][0]["elements"][0]["content"] == "Editado"
    assert callback.await_count == 2
