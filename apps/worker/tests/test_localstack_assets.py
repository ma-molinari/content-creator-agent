"""Opt-in verification of immutable worker uploads against local LocalStack."""

import os
from urllib.parse import urlsplit
from uuid import uuid4

import boto3
import pytest

from app.immutable_assets import _put_immutable


def test_immutable_upload_against_localstack():
    endpoint = os.getenv("LOCALSTACK_TEST_ENDPOINT")
    if not endpoint:
        pytest.skip("LOCALSTACK_TEST_ENDPOINT not configured")
    parsed = urlsplit(endpoint)
    assert parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    client = boto3.client("s3", endpoint_url=endpoint, region_name="us-east-1", aws_access_key_id="test", aws_secret_access_key="test")
    key = "integration-test/" + str(uuid4())
    try:
        _put_immutable(client, "postmind-local", key, b"first", "application/octet-stream")
        _put_immutable(client, "postmind-local", key, b"first", "application/octet-stream")
        with pytest.raises(ValueError, match="different content"):
            _put_immutable(client, "postmind-local", key, b"second", "application/octet-stream")
        body = client.get_object(Bucket="postmind-local", Key=key)["Body"]
        try:
            assert body.read() == b"first"
        finally:
            body.close()
    finally:
        client.delete_object(Bucket="postmind-local", Key=key)
