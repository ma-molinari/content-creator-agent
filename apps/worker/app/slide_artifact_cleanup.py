"""Best-effort removal of orphaned slide objects when a job fails after partial uploads."""

from __future__ import annotations

import logging
from typing import Sequence

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import Settings

logger = logging.getLogger(__name__)

_BATCH = 900  # Leave headroom below S3 DeleteObjects API limit.


def delete_slide_artifact_keys_sync(settings: Settings, keys: Sequence[str]) -> None:
    """Deletes the given keys (expected under slides/<job_id>/...) using DeleteObjects batches."""
    unique = tuple({k.strip() for k in keys if (k or "").strip()})
    if not unique:
        return

    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    bucket = settings.aws_s3_bucket

    for i in range(0, len(unique), _BATCH):
        chunk = list(unique[i : i + _BATCH])
        try:
            resp = client.delete_objects(
                Bucket=bucket,
                Delete={"Objects": [{"Key": k} for k in chunk], "Quiet": True},
            )
        except (ClientError, BotoCoreError) as exc:
            logger.warning("slide cleanup delete_objects failed bucket=%s err=%s", bucket, exc)
            continue

        errs = resp.get("Errors") or []
        for err in errs:
            logger.warning(
                "slide cleanup key failed bucket=%s key=%s code=%s",
                bucket,
                err.get("Key"),
                err.get("Code"),
            )
