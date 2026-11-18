"""Copy authorized image assets into an immutable job prefix."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Mapping
from uuid import UUID

from app.post_document import ImageElement, PostDocumentV1

_MAX_BYTES = 5 * 1024 * 1024


class AssetCopyError(Exception):
    def __init__(self, attempted_keys: list[str]):
        super().__init__("Não foi possível preservar as imagens do post.")
        self.attempted_keys = tuple(attempted_keys)


@dataclass(frozen=True)
class CopiedAssets:
    keys: dict[str, str]
    contents: dict[str, bytes]


def _extension_and_type(data: bytes) -> tuple[str, str]:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    raise ValueError("unsupported image format")


def _read_image(client, bucket: str, key: str) -> bytes:
    response = client.get_object(Bucket=bucket, Key=key)
    body = response["Body"]
    try:
        data = body.read(_MAX_BYTES + 1)
    finally:
        body.close()
    if len(data) > _MAX_BYTES:
        raise ValueError("image exceeds size limit")
    return data


async def copy_version_assets(
    document: PostDocumentV1, *, job_id: str, bucket: str,
    authorized_sources: Mapping[str, str], client,
) -> CopiedAssets:
    """The source mapping must be supplied by the API after ownership validation."""
    document = PostDocumentV1.model_validate_json(document.model_dump_json(by_alias=True))
    job_uuid = UUID(job_id)
    used_ids = sorted({item.asset_id for slide in document.slides for item in slide.elements if isinstance(item, ImageElement)})
    if any(asset_id not in authorized_sources or not authorized_sources[asset_id] for asset_id in used_ids):
        raise ValueError("image asset is not authorized")
    keys: dict[str, str] = {}
    contents: dict[str, bytes] = {}
    attempted: list[str] = []
    try:
        for asset_id in used_ids:
            data = await asyncio.to_thread(_read_image, client, bucket, authorized_sources[asset_id])
            extension, content_type = _extension_and_type(data)
            key = f"slides/{job_uuid}/assets/{asset_id}.{extension}"
            attempted.append(key)
            await asyncio.to_thread(client.put_object, Bucket=bucket, Key=key, Body=data, ContentType=content_type)
            keys[asset_id] = key
            contents[asset_id] = data
        manifest_key = f"slides/{job_uuid}/assets.json"
        attempted.append(manifest_key)
        manifest = json.dumps(keys, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
        await asyncio.to_thread(client.put_object, Bucket=bucket, Key=manifest_key, Body=manifest, ContentType="application/json")
    except Exception as exc:
        # An upload may have succeeded even if its response was lost; defer cleanup to reconciliation.
        raise AssetCopyError(attempted) from exc
    return CopiedAssets(keys=keys, contents=contents)
