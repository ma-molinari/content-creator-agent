"""Upload rendered JPEGs to S3 with exponential backoff."""

import asyncio
import logging
import re
from typing import Optional

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings
from app.state import AgentState, ArtifactRef

logger = logging.getLogger(__name__)

_MAX_ATTEMPTS = 3


def _slide_number_from_filename(filename: str) -> int:
    base = filename.rsplit(".", 1)[0]
    m = re.search(r"(\d+)", base)
    if m:
        return int(m.group(1))
    return 0


def _put_object_sync(client, bucket: str, key: str, body: bytes) -> None:
    """Blocking S3 put — intended to be called via asyncio.to_thread."""
    client.put_object(Bucket=bucket, Key=key, Body=body, ContentType="image/jpeg")


async def _upload_with_retry(client, bucket: str, key: str, body: bytes) -> None:
    delay = 0.5
    last: Optional[Exception] = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            await asyncio.to_thread(_put_object_sync, client, bucket, key, body)
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
    errors = list(state.get("errors") or [])

    if not rendered:
        return {"artifacts": [], "errors": errors}

    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    bucket = settings.aws_s3_bucket

    artifacts: list[ArtifactRef] = []
    for idx, item in enumerate(rendered, start=1):
        fname = item.get("filename") or "slide.jpeg"
        body = item.get("jpeg_bytes") or b""
        key = f"slides/{job_id}/{fname}"
        try:
            await _upload_with_retry(client, bucket, key, body)
            sn = _slide_number_from_filename(fname)
            if sn <= 0:
                sn = idx
            artifacts.append(
                {
                    "s3_key": key,
                    "slide_number": sn,
                }
            )
        except (ClientError, BotoCoreError) as e:
            errors.append(f"upload_assets {key}: {e!s}")

    return {"artifacts": artifacts, "errors": errors}
