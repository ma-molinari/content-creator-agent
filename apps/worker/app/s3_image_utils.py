"""Shared helpers for fetching and typing images from S3."""

from __future__ import annotations

import mimetypes
from urllib.parse import urlparse
from typing import Mapping, Protocol, cast

from pydantic import ValidationError

from app.config import get_settings


class _S3PresignClient(Protocol):
    def generate_presigned_url(
        self,
        ClientMethod: str,
        Params: dict[str, str],
        ExpiresIn: int,
    ) -> str:
        ...
class _StreamingBody(Protocol):
    def read(self, amt: int = ...) -> bytes: ...


class _S3GetObjectClient(Protocol):
    def get_object(self, Bucket: str, Key: str) -> Mapping[str, object]: ...


def guess_mime(data: bytes, s3_key: str) -> str:
    if len(data) >= 3 and data[0:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(data) >= 8 and data[0:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 6 and (data[0:6] in (b"GIF87a", b"GIF89a")):
        return "image/gif"
    ext = s3_key.rsplit(".", 1)
    if len(ext) == 2:
        mt = mimetypes.guess_type("x." + ext[1].lower())[0]
        if mt and mt.startswith("image/"):
            return mt
    return "image/jpeg"


def fetch_bytes_limited(client: _S3GetObjectClient, bucket: str, key: str, max_bytes: int) -> bytes:
    o = client.get_object(Bucket=bucket, Key=key)
    body_raw = o["Body"]
    body = cast(_StreamingBody, body_raw)
    chunk = body.read(max_bytes + 1)
    if len(chunk) > max_bytes:
        raise ValueError(f"reference object exceeds configured max ({max_bytes} bytes)")
    return chunk


def presign_get_url(client: _S3PresignClient, bucket: str, key: str, expires_in_seconds: int = 3600) -> str:
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in_seconds,
    )


def allowed_s3_hosts(bucket: str | None = None, region: str | None = None) -> frozenset[str]:
    if bucket is None or region is None:
        try:
            settings = get_settings()
        except ValidationError:
            return frozenset()
        bucket = bucket or settings.aws_s3_bucket
        region = region or settings.aws_region
    bucket = (bucket or "").strip()
    region = (region or "").strip()
    if not bucket or not region:
        return frozenset()
    return frozenset(
        {
            f"{bucket}.s3.{region}.amazonaws.com",
            f"{bucket}.s3.amazonaws.com",
            f"s3.{region}.amazonaws.com",
            "s3.amazonaws.com",
        }
    )


def is_allowed_s3_url(url: str, bucket: str | None = None, region: str | None = None) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    if not host:
        return False
    hosts = allowed_s3_hosts(bucket, region)
    if host not in hosts:
        return False
    if bucket and host in {f"s3.{region}.amazonaws.com", "s3.amazonaws.com"}:
        return parsed.path.startswith(f"/{bucket}/")
    return True
