"""Tests for isolated asset copies; authorization is supplied by the API."""

import asyncio
import io
from uuid import uuid4

import pytest

from app.immutable_assets import AssetCopyError, copy_version_assets
from app.post_document import PostDocumentV1


def document(ids):
    return PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{
        "id": "s", "layout": "hero", "background": {"type": "solid", "color": "#000000"},
        "elements": [{"id": f"i{i}", "type": "image", "assetId": asset_id, "fit": "cover"} for i, asset_id in enumerate(ids)],
    }]})


class FakeS3:
    def __init__(self, objects, fail_at=None):
        self.objects = objects
        self.uploaded = {}
        self.fail_at = fail_at
    def get_object(self, Bucket, Key): return {"Body": io.BytesIO(self.objects[Key])}
    def put_object(self, Bucket, Key, Body, ContentType):
        if self.fail_at is not None and len(self.uploaded) == self.fail_at:
            raise RuntimeError("failed")
        self.uploaded[Key] = (Body, ContentType)


def test_copies_current_and_inherited_assets():
    png = b"\x89PNG\r\n\x1a\nimage"
    client = FakeS3({"users/u/current": png, "slides/old/inherited": png})
    job_id = str(uuid4())
    result = asyncio.run(copy_version_assets(document(["a", "b"]), job_id=job_id, bucket="test", authorized_sources={"a": "users/u/current", "b": "slides/old/inherited"}, client=client))
    assert result.keys == {"a": f"slides/{job_id}/assets/a.png", "b": f"slides/{job_id}/assets/b.png"}
    client.objects.clear()
    assert result.contents == {"a": png, "b": png}
    assert all(value[1] == "image/png" for value in client.uploaded.values())


def test_rejects_unknown_id_before_any_upload():
    client = FakeS3({})
    with pytest.raises(ValueError, match="not authorized"):
        asyncio.run(copy_version_assets(document(["a"]), job_id=str(uuid4()), bucket="test", authorized_sources={}, client=client))
    assert client.uploaded == {}


def test_partial_upload_includes_uncertain_key_for_reconciliation():
    png = b"\x89PNG\r\n\x1a\nimage"
    client = FakeS3({"x": png, "y": png}, fail_at=1)
    job_id = str(uuid4())
    with pytest.raises(AssetCopyError) as exc:
        asyncio.run(copy_version_assets(document(["a", "b"]), job_id=job_id, bucket="test", authorized_sources={"a": "x", "b": "y"}, client=client))
    assert exc.value.attempted_keys == (f"slides/{job_id}/assets/a.png", f"slides/{job_id}/assets/b.png")
