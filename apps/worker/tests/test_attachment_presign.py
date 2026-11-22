"""Verify attachment URLs use the resolved S3 endpoint and Signature V4."""

import asyncio
from types import SimpleNamespace
from unittest import TestCase, main
from unittest.mock import MagicMock, patch

from app.nodes import describe_user_attachments as node


class AttachmentPresignTest(TestCase):
    def test_presign_uses_resolved_endpoint_and_sigv4(self):
        settings = SimpleNamespace(
            aws_region="us-east-2", aws_access_key_id="test", aws_secret_access_key="test",
            aws_s3_bucket="bucket", reference_image_max_bytes=1024,
        )
        reader = MagicMock()
        reader.meta.endpoint_url = "https://s3.us-east-2.amazonaws.com"
        signer = MagicMock()
        signer.generate_presigned_url.return_value = "https://signed.example/image"
        clients = MagicMock(side_effect=[reader, signer])
        with patch.object(node, "get_settings", return_value=settings), \
             patch.object(node, "read_prompt_md", return_value="prompt"), \
             patch.object(node.boto3, "client", clients), \
             patch.object(node, "fetch_bytes_limited", side_effect=ValueError("too large")):
            result = asyncio.run(node.describe_user_attachments({"user_attachment_s3_keys": ["image.png"]}))

        kwargs = clients.call_args_list[1].kwargs
        self.assertEqual(kwargs["endpoint_url"], reader.meta.endpoint_url)
        self.assertEqual(kwargs["config"].signature_version, "s3v4")
        self.assertEqual(result["user_attachment_signed_urls"], ["https://signed.example/image"])


if __name__ == "__main__":
    main()
