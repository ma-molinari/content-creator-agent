"""Publish immutable structured artifacts and retry the same completion callback."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Mapping
from uuid import UUID

from app.api_client import post_complete_callback
from app.immutable_assets import CopiedAssets, _put_immutable
from app.post_document import ImageElement, PostDocumentV1
from app.post_document_v2 import PostDocumentV2
from app.post_document_v3 import PostDocumentV3, used_asset_ids as used_v3_assets
from app.post_renderer import RENDERER_VERSION
from app.state import RenderedSlide, SlideItem


class StructuredCallbackUnknown(Exception):
    """The callback may have committed; do not send a failure callback."""


class StructuredCompletionRejected(Exception):
    """The API explicitly rejected a structured completion."""


class StructuredUploadError(Exception):
    def __init__(self, attempted_keys: list[str]):
        super().__init__("Não foi possível salvar os arquivos do post.")
        self.attempted_keys = tuple(attempted_keys)


@dataclass(frozen=True)
class StructuredUpload:
    document_key: str
    artifacts: list[dict[str, object]]


async def upload_structured_post(
    document: PostDocumentV1 | PostDocumentV2 | PostDocumentV3, slides: list[SlideItem], images: list[RenderedSlide], assets: CopiedAssets,
    *, job_id: str, bucket: str, client,
) -> StructuredUpload:
    document = type(document).model_validate_json(document.model_dump_json(by_alias=True))
    prefix = f"slides/{UUID(job_id)}/"
    used = (used_v3_assets(document) if isinstance(document, PostDocumentV3) else
            {item.asset_id for slide in document.slides for item in slide.elements if isinstance(item, ImageElement)})
    if set(assets.keys) != used or set(assets.contents) != used:
        raise ValueError("asset manifest does not match document")
    if len(slides) != len(document.slides) or len(images) != len(slides):
        raise ValueError("slide artifacts are incomplete")
    payloads: list[tuple[str, bytes, str]] = []
    doc_bytes = document.model_dump_json(by_alias=True).encode("utf-8")
    if len(doc_bytes) > 2 * 1024 * 1024:
        raise ValueError("document exceeds size limit")
    payloads.append((prefix + "document.json", doc_bytes, "application/json; charset=utf-8"))
    artifacts: list[dict[str, object]] = []
    for index, (slide, image) in enumerate(zip(slides, images), start=1):
        base = f"slide_{index:02d}"
        html, jpeg = slide.get("html") or "", image.get("jpeg_bytes") or b""
        if slide.get("filename") != base + ".html" or image.get("filename") != base + ".jpeg" or not html or not jpeg.startswith(b"\xff\xd8\xff"):
            raise ValueError("invalid slide artifacts")
        html_key, jpeg_key = prefix + base + ".html", prefix + base + ".jpeg"
        payloads.extend([(html_key, html.encode("utf-8"), "text/html; charset=utf-8"), (jpeg_key, jpeg, "image/jpeg")])
        artifacts.append({"s3Key": jpeg_key, "slideNumber": index, "htmlS3Key": html_key})
    attempted: list[str] = []
    try:
        # Manifest and asset keys were written by copy_version_assets before publication.
        await asyncio.to_thread(client.head_object, Bucket=bucket, Key=prefix + "assets.json")
        for asset_id, key in assets.keys.items():
            if key not in {prefix + "assets/" + asset_id + "." + ext for ext in ("jpg", "png", "webp")}:
                raise ValueError("asset key outside job prefix")
            await asyncio.to_thread(client.head_object, Bucket=bucket, Key=key)
        for key, data, content_type in payloads:
            attempted.append(key)
            await asyncio.to_thread(_put_immutable, client, bucket, key, data, content_type)
    except Exception as exc:
        raise StructuredUploadError(attempted) from exc
    return StructuredUpload(document_key=prefix + "document.json", artifacts=artifacts)


async def send_structured_completion(
    url: str, *, api_key: str, assistant_text: str, upload: StructuredUpload,
    schema_version: int = 1, renderer_version: str = RENDERER_VERSION,
) -> int:
    payload: Mapping[str, object] = {
        "assistantText": assistant_text,
        "artifacts": upload.artifacts,
        "structured": {"documentS3Key": upload.document_key, "schemaVersion": schema_version, "rendererVersion": renderer_version},
        "error": None,
    }
    # The shared client retries the same payload on transport errors and 5xx.
    # Never send a failure callback or delete artifacts solely because the response is unknown.
    try:
        response = await post_complete_callback(url, json_body=payload, headers={"X-Worker-API-Key": api_key}, timeout=15.0)
    except Exception as exc:
        raise StructuredCallbackUnknown("O resultado do callback é desconhecido.") from exc
    if response.status_code >= 500:
        raise StructuredCallbackUnknown("O resultado do callback é desconhecido.")
    if response.status_code >= 400 and response.status_code != 409:
        raise StructuredCompletionRejected("O resultado estruturado foi rejeitado.")
    return response.status_code
