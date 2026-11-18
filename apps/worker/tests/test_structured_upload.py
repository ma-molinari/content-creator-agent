"""Tests for structured artifact upload and callback safety."""

import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from app.immutable_assets import CopiedAssets
from app.post_document import PostDocumentV1
from app.structured_upload import StructuredUploadError, send_structured_completion, upload_structured_post


class FakeS3:
    def __init__(self, prefix, fail_at=None):
        self.existing = {prefix + "assets.json"}
        self.uploaded = {}
        self.fail_at = fail_at
    def head_object(self, Bucket, Key):
        if Key not in self.existing: raise ValueError("missing")
    def put_object(self, **kwargs):
        if self.fail_at == len(self.uploaded): raise RuntimeError("upload failed")
        assert kwargs["IfNoneMatch"] == "*"
        self.uploaded[kwargs["Key"]] = kwargs["Body"]


def make_document():
    return PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{"id": "s", "layout": "hero", "background": {"type": "solid", "color": "#000000"}, "elements": [{"id": "t", "type": "text", "role": "heading", "content": "Oi", "style": {"color": "#FFFFFF", "size": "large"}}]}]})


def inputs():
    return ([{"filename": "slide_01.html", "html": "<html></html>"}], [{"filename": "slide_01.jpeg", "jpeg_bytes": b"\xff\xd8\xffjpeg"}])


def test_upload_returns_callback_keys():
    job_id = str(uuid4()); prefix = f"slides/{job_id}/"; client = FakeS3(prefix)
    slides, images = inputs()
    result = asyncio.run(upload_structured_post(make_document(), slides, images, CopiedAssets({}, {}), job_id=job_id, bucket="test", client=client))
    assert result.document_key == prefix + "document.json"
    assert result.artifacts[0]["s3Key"] == prefix + "slide_01.jpeg"
    assert set(client.uploaded) == {prefix + "document.json", prefix + "slide_01.html", prefix + "slide_01.jpeg"}


def test_partial_failure_records_all_attempted_keys():
    job_id = str(uuid4()); prefix = f"slides/{job_id}/"; client = FakeS3(prefix, fail_at=1)
    slides, images = inputs()
    with pytest.raises(StructuredUploadError) as exc:
        asyncio.run(upload_structured_post(make_document(), slides, images, CopiedAssets({}, {}), job_id=job_id, bucket="test", client=client))
    assert exc.value.attempted_keys == (prefix + "document.json", prefix + "slide_01.html")


def test_incomplete_artifacts_are_rejected_before_upload():
    job_id = str(uuid4()); client = FakeS3(f"slides/{job_id}/")
    with pytest.raises(ValueError, match="incomplete"):
        asyncio.run(upload_structured_post(make_document(), [], [], CopiedAssets({}, {}), job_id=job_id, bucket="test", client=client))
    assert not client.uploaded


def test_timeout_never_sends_failure_callback(monkeypatch):
    job_id = str(uuid4()); client = FakeS3(f"slides/{job_id}/"); slides, images = inputs()
    upload = asyncio.run(upload_structured_post(make_document(), slides, images, CopiedAssets({}, {}), job_id=job_id, bucket="test", client=client))
    send = AsyncMock(side_effect=httpx.ReadTimeout("timeout"))
    monkeypatch.setattr("app.structured_upload.post_complete_callback", send)
    with pytest.raises(httpx.ReadTimeout):
        asyncio.run(send_structured_completion("http://api/internal/jobs/x/complete", api_key="key", assistant_text="ok", upload=upload))
    assert send.await_count == 1
    assert send.await_args.kwargs["json_body"]["error"] is None
    assert len(client.uploaded) == 3
