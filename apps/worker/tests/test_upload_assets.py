"""Tests for upload_assets S3 uploads (JPEG + optional HTML source)."""

from __future__ import annotations

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from botocore.exceptions import ClientError

from app.nodes.upload_assets import upload_assets

_HTML = "<html><body>" + ("x" * 100) + "</body></html>"


class TestUploadAssets(IsolatedAsyncioTestCase):
    def _settings(self, *, require_html: bool = False) -> MagicMock:
        mock = MagicMock()
        mock.aws_region = "us-east-1"
        mock.aws_access_key_id = "ak"
        mock.aws_secret_access_key = "sk"
        mock.aws_s3_bucket = "bucket"
        mock.require_html_artifact_upload = require_html
        return mock

    async def test_uploads_jpeg_and_html_put_object_twice(self) -> None:
        keys_put: list[str] = []

        def put_object_capture(**kwargs: object) -> None:
            keys_put.append(str(kwargs["Key"]))
            ctype = kwargs.get("ContentType", "")
            if "jpeg" in str(ctype):
                assert "slide_01.jpeg" in keys_put[-1]

        client = MagicMock()
        client.put_object.side_effect = put_object_capture

        with (
            patch("app.nodes.upload_assets.boto3.client", return_value=client),
            patch("app.nodes.upload_assets.get_settings", return_value=self._settings()),
            patch("app.nodes.upload_assets.asyncio.sleep", new_callable=AsyncMock),
        ):
            state = {
                "job_id": "00000000-0000-0000-0000-000000000001",
                "errors": [],
                "rendered_slides": [{"filename": "slide_01.jpeg", "jpeg_bytes": b"\xff\xd8"}],
                "slides_html": [{"filename": "slide_01.html", "html": _HTML}],
            }
            out = await upload_assets(state)  # type: ignore[arg-type]

        self.assertEqual(keys_put[0].endswith("slide_01.jpeg"), True)
        self.assertEqual(keys_put[1].endswith("slide_01.html"), True)
        artifacts = out.get("artifacts") or []
        self.assertEqual(len(artifacts), 1)
        self.assertEqual(artifacts[0]["html_s3_key"], keys_put[1])
        self.assertEqual(len(out.get("errors") or []), 0)

    async def test_html_upload_failure_appends_errors_jpeg_still_uploaded(self) -> None:

        def put_object_capture(**kwargs: object) -> None:
            ctype = str(kwargs.get("ContentType") or "")
            if "image/jpeg" in ctype:
                return
            raise ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "denied"}},
                "PutObject",
            )

        client = MagicMock()
        client.put_object.side_effect = put_object_capture

        jid = "00000000-0000-0000-0000-000000000002"

        with (
            patch("app.nodes.upload_assets.boto3.client", return_value=client),
            patch("app.nodes.upload_assets.get_settings", return_value=self._settings()),
            patch("app.nodes.upload_assets.asyncio.sleep", new_callable=AsyncMock),
        ):
            out = await upload_assets(
                {
                    "job_id": jid,
                    "errors": [],
                    "rendered_slides": [{"filename": "slide_01.jpeg", "jpeg_bytes": b"\xff\xd8"}],
                    "slides_html": [{"filename": "slide_01.html", "html": _HTML}],
                },  # type: ignore[arg-type]
            )

        errs = out.get("errors") or []
        self.assertTrue(any(e.startswith(f"upload_assets slides/{jid}/slide_01.html") for e in errs))
        art = (out.get("artifacts") or [])[0]
        self.assertIsNone(art.get("html_s3_key"))

    async def test_require_html_missing_source_reports_error(self) -> None:
        client = MagicMock()
        jid = "00000000-0000-0000-0000-000000000003"

        with (
            patch("app.nodes.upload_assets.boto3.client", return_value=client),
            patch("app.nodes.upload_assets.get_settings", return_value=self._settings(require_html=True)),
            patch("app.nodes.upload_assets.asyncio.sleep", new_callable=AsyncMock),
        ):
            out = await upload_assets(
                {
                    "job_id": jid,
                    "errors": [],
                    "rendered_slides": [{"filename": "slide_01.jpeg", "jpeg_bytes": b"\xff\xd8"}],
                    "slides_html": [],
                },  # type: ignore[arg-type]
            )

        errs = out.get("errors") or []
        self.assertTrue(any("missing html source" in e for e in errs))
        self.assertIsNone((out.get("artifacts") or [{}])[0].get("html_s3_key"))
