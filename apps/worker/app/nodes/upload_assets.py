"""Upload rendered JPEGs to S3 with exponential backoff."""

import asyncio
import json
import logging
import re

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings
from app.state import AgentState, ArtifactRef, copy_errors

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3


def _slide_number_from_filename(filename: str) -> int:
    base = filename.rsplit(".", 1)[0]
    m = re.search(r"(\d+)", base)
    if m:
        return int(m.group(1))
    return 0


def _put_object_sync(
    client, bucket: str, key: str, body: bytes, content_type: str
) -> None:
    """Blocking S3 put — intended to be called via asyncio.to_thread."""
    client.put_object(Bucket=bucket, Key=key, Body=body, ContentType=content_type)


async def _upload_with_retry(
    client, bucket: str, key: str, body: bytes, *, content_type: str
) -> None:
    delay = 0.5
    last: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            await asyncio.to_thread(
                _put_object_sync, client, bucket, key, body, content_type
            )
            return
        except (ClientError, BotoCoreError) as e:
            last = e
            if attempt < _MAX_ATTEMPTS - 1:
                await asyncio.sleep(delay)
                delay *= 2
    if last:
        raise last


async def upload_assets(state: AgentState) -> dict:
    logger.info("node=upload_assets job_id=%s", state.get("job_id"))
    settings = get_settings()
    job_id = state.get("job_id") or ""
    rendered = state.get("rendered_slides") or []
    errors = copy_errors(state)

    if not rendered:
        return {"artifacts": [], "errors": errors}

    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    bucket = settings.aws_s3_bucket
    uploaded_source_key: str | None = None
    package = state.get("slide_package")
    if package:
        source_key = f"slides/{job_id}/slide_package.json"
        try:
            await _upload_with_retry(
                client,
                bucket,
                source_key,
                json.dumps(package, ensure_ascii=False).encode("utf-8"),
                content_type="application/json; charset=utf-8",
            )
            uploaded_source_key = source_key
        except (ClientError, BotoCoreError) as e:
            logger.error("node=upload_assets job_id=%s source=%s err=%s", job_id, source_key, e)
            errors.append(f"upload_assets {source_key}: {e!s}")

    slides_html = state.get("slides_html") or []
    html_by_filename: dict[str, str] = {}
    for s in slides_html:
        fn = (s.get("filename") or "").strip()
        if fn:
            html_by_filename[fn] = s.get("html") or ""

    artifacts: list[ArtifactRef] = []
    for idx, item in enumerate(rendered, start=1):
        fname = item.get("filename") or "slide.jpeg"
        body = item.get("jpeg_bytes") or b""
        key = f"slides/{job_id}/{fname}"
        try:
            await _upload_with_retry(
                client, bucket, key, body, content_type="image/jpeg"
            )
            sn = _slide_number_from_filename(fname)
            if sn <= 0:
                sn = idx
            html_fname = fname.rsplit(".", 1)[0] + ".html"
            html_key = f"slides/{job_id}/{html_fname}"
            html_content = html_by_filename.get(fname) or html_by_filename.get(html_fname)
            html_s3_key: str | None = None
            if html_content:
                try:
                    await _upload_with_retry(
                        client,
                        bucket,
                        html_key,
                        html_content.encode("utf-8"),
                        content_type="text/html; charset=utf-8",
                    )
                    html_s3_key = html_key
                except (ClientError, BotoCoreError) as e:
                    logger.error(
                        "node=upload_assets job_id=%s slide=%s err=%s",
                        job_id,
                        html_key,
                        e,
                    )
                    errors.append(f"upload_assets {html_key}: {e!s}")
            elif settings.require_html_artifact_upload:
                errors.append(f"upload_assets missing html source for {fname} (expected {html_key})")
            artifacts.append(
                {
                    "s3_key": key,
                    "slide_number": sn,
                    "html_s3_key": html_s3_key,
                }
            )
        except (ClientError, BotoCoreError) as e:
            errors.append(f"upload_assets {key}: {e!s}")

    out: dict[str, object] = {"artifacts": artifacts, "errors": errors}
    if uploaded_source_key:
        metadata = dict(state.get("worker_metadata") or {})
        metadata["slidePackageS3Key"] = uploaded_source_key
        out["worker_metadata"] = metadata
    return out
