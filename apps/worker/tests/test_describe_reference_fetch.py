"""Tests for S3 fetch limits in describe_references."""

from __future__ import annotations

from unittest import TestCase
from unittest.mock import MagicMock

from app.nodes import describe_references as dr


class TestDescribeReferenceFetch(TestCase):
    def test_fetch_bytes_limited_rejects_overflow(self) -> None:
        fake_body = MagicMock()
        fake_body.read.side_effect = [b"a" * 11]

        fake_client = MagicMock()
        fake_client.get_object.return_value = {"Body": fake_body}

        with self.assertRaisesRegex(ValueError, "exceeds configured max"):
            dr._fetch_bytes_limited(fake_client, "b", "k/ref.png", 10)

    def test_fetch_bytes_limited_allows_exact_size(self) -> None:
        data = b"z" * 10
        fake_body = MagicMock()
        fake_body.read.side_effect = [data]

        fake_client = MagicMock()
        fake_client.get_object.return_value = {"Body": fake_body}

        got = dr._fetch_bytes_limited(fake_client, "bucket", "k/ref.png", 10)

        self.assertEqual(got, data)
