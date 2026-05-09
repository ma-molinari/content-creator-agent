"""Unit tests for finalize callback decision and partial-upload cleanup."""

from __future__ import annotations

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.nodes.finalize import finalize
from app.nodes.finalize_messages import (
    JOB_FAILURE_GENERIC,
    JOB_FAILURE_HTML_ARTIFACT,
    JOB_FAILURE_INCOMPLETE_CAROUSEL,
    JOB_FAILURE_REFINEMENT_CONTEXT,
)
from app.prompt_security import USER_PROFILE_TEXT_TOO_LONG_MESSAGE, USER_PROMPT_REJECT_MESSAGE


def _minimal_state(**kwargs: object) -> dict:
    base = {
        "job_id": "job-1",
        "user_id": "u",
        "chat_id": "c",
        "raw_message": "",
        "audit_text": "",
        "brand_text": "",
        "profile_text": "",
        "optimized_brief": "",
        "raw_slide_output": "",
        "slides_html": [],
        "rendered_slides": [],
        "artifacts": [],
        "retry_count": 0,
        "errors": [],
    }
    base.update(kwargs)
    return base


class TestFinalize(IsolatedAsyncioTestCase):
    async def test_success_when_artifacts_match_rendered_despite_reference_errors(self) -> None:
        ok = httpx.Response(204)
        settings_mock = MagicMock()
        settings_mock.go_api_url = "http://api"
        settings_mock.worker_api_key = "k"
        settings_mock.require_html_artifact_upload = False

        artifacts = [
            {"s3_key": "slides/job-1/slide_01.jpeg", "slide_number": 1},
            {"s3_key": "slides/job-1/slide_02.jpeg", "slide_number": 2},
        ]
        rendered = [
            {"filename": "slide_01.jpeg", "jpeg_bytes": b"a"},
            {"filename": "slide_02.jpeg", "jpeg_bytes": b"b"},
        ]
        errors = ["describe_references: falha ao baixar referência S3 x: boom"]

        with (
            patch("app.nodes.finalize.get_settings", return_value=settings_mock),
            patch("app.nodes.finalize.post_complete_callback", new_callable=AsyncMock) as post,
        ):
            post.return_value = ok
            out = await finalize(
                _minimal_state(
                    artifacts=artifacts,
                    rendered_slides=rendered,
                    errors=errors,
                ),
            )

        post.assert_called_once()
        kw = post.await_args.kwargs
        body = kw["json_body"]
        self.assertEqual(body.get("error"), None)
        self.assertEqual(len(body.get("artifacts")), 2)
        self.assertEqual(out.get("artifacts"), None)

    async def test_failure_mismatch_triggers_error_payload_and_cleanup(self) -> None:
        resp = httpx.Response(204)
        settings_mock = MagicMock()
        settings_mock.go_api_url = "http://api"
        settings_mock.worker_api_key = "k"
        settings_mock.require_html_artifact_upload = False

        artifacts = [{"s3_key": "slides/job-1/slide_01.jpeg", "slide_number": 1}]
        rendered = [
            {"filename": "slide_01.jpeg", "jpeg_bytes": b"a"},
            {"filename": "slide_02.jpeg", "jpeg_bytes": b"b"},
        ]
        cleanup_called: dict[str, int] = {"n": 0}

        async def fake_to_thread(fn, *args):  # noqa: ANN001
            if fn.__name__ == "delete_slide_artifact_keys_sync":
                cleanup_called["n"] += 1
            return None

        with (
            patch("app.nodes.finalize.get_settings", return_value=settings_mock),
            patch("app.nodes.finalize.post_complete_callback", new_callable=AsyncMock) as post,
            patch("app.nodes.finalize.asyncio.to_thread", new_callable=AsyncMock, side_effect=fake_to_thread),
        ):
            post.return_value = resp
            await finalize(
                _minimal_state(
                    artifacts=artifacts,
                    rendered_slides=rendered,
                    errors=["upload_assets slides/job-1/slide_02.jpeg: boom"],
                ),
            )

        self.assertGreaterEqual(post.await_count, 1)
        first = post.await_args_list[0].kwargs["json_body"]
        self.assertIn("error", first)
        self.assertEqual(first["error"], JOB_FAILURE_INCOMPLETE_CAROUSEL)
        self.assertEqual(cleanup_called["n"], 1)

    async def test_no_artifact_validation_failure_uses_generic_error(self) -> None:
        resp = httpx.Response(204)
        settings_mock = MagicMock()
        settings_mock.go_api_url = "http://api"
        settings_mock.worker_api_key = "k"
        settings_mock.require_html_artifact_upload = False

        with (
            patch("app.nodes.finalize.get_settings", return_value=settings_mock),
            patch("app.nodes.finalize.post_complete_callback", new_callable=AsyncMock) as post,
        ):
            post.return_value = resp
            await finalize(
                _minimal_state(
                    requested_slide_count=4,
                    artifacts=[],
                    rendered_slides=[],
                    errors=["slide_package: esperados 4 slides; recebidos 0."],
                ),
            )

        first = post.await_args_list[0].kwargs["json_body"]
        self.assertEqual(first["error"], JOB_FAILURE_GENERIC)
        self.assertEqual(first["errorCode"], "worker_failed")

    async def test_security_rejection_preserves_prompt_message(self) -> None:
        resp = httpx.Response(204)
        settings_mock = MagicMock()
        settings_mock.go_api_url = "http://api"
        settings_mock.worker_api_key = "k"
        settings_mock.require_html_artifact_upload = False

        with (
            patch("app.nodes.finalize.get_settings", return_value=settings_mock),
            patch("app.nodes.finalize.post_complete_callback", new_callable=AsyncMock) as post,
        ):
            post.return_value = resp
            await finalize(
                _minimal_state(
                    errors=[USER_PROMPT_REJECT_MESSAGE],
                ),
            )

        body = post.await_args.kwargs["json_body"]
        self.assertEqual(body["error"], USER_PROMPT_REJECT_MESSAGE)

    async def test_profile_text_too_long_preserves_profile_message(self) -> None:
        resp = httpx.Response(204)
        settings_mock = MagicMock()
        settings_mock.go_api_url = "http://api"
        settings_mock.worker_api_key = "k"
        settings_mock.require_html_artifact_upload = False

        with (
            patch("app.nodes.finalize.get_settings", return_value=settings_mock),
            patch("app.nodes.finalize.post_complete_callback", new_callable=AsyncMock) as post,
        ):
            post.return_value = resp
            await finalize(
                _minimal_state(
                    errors=[USER_PROFILE_TEXT_TOO_LONG_MESSAGE],
                ),
            )

        body = post.await_args.kwargs["json_body"]
        self.assertEqual(body["error"], USER_PROFILE_TEXT_TOO_LONG_MESSAGE)

    async def test_refinement_context_error_overrides_carousel_mismatch(self) -> None:
        """When refinement failed but mismatch_delivery is also true, user sees refinement copy."""
        resp = httpx.Response(204)
        settings_mock = MagicMock()
        settings_mock.go_api_url = "http://api"
        settings_mock.worker_api_key = "k"
        settings_mock.require_html_artifact_upload = False

        artifacts = [{"s3_key": "slides/job-1/slide_01.jpeg", "slide_number": 1}]
        rendered = [
            {"filename": "slide_01.jpeg", "jpeg_bytes": b"a"},
            {"filename": "slide_02.jpeg", "jpeg_bytes": b"b"},
        ]

        with (
            patch("app.nodes.finalize.get_settings", return_value=settings_mock),
            patch("app.nodes.finalize.post_complete_callback", new_callable=AsyncMock) as post,
            patch("app.nodes.finalize.asyncio.to_thread", new_callable=AsyncMock, return_value=None),
        ):
            post.return_value = resp
            await finalize(
                _minimal_state(
                    artifacts=artifacts,
                    rendered_slides=rendered,
                    errors=[JOB_FAILURE_REFINEMENT_CONTEXT, "other"],
                ),
            )

        first = post.await_args_list[0].kwargs["json_body"]
        self.assertEqual(first["error"], JOB_FAILURE_REFINEMENT_CONTEXT)

    async def test_require_html_gap_triggers_failure_callback_and_cleanup(self) -> None:
        resp = httpx.Response(204)
        settings_mock = MagicMock()
        settings_mock.go_api_url = "http://api"
        settings_mock.worker_api_key = "k"
        settings_mock.require_html_artifact_upload = True

        artifacts = [
            {"s3_key": "slides/job-1/slide_01.jpeg", "slide_number": 1},
        ]
        rendered = [{"filename": "slide_01.jpeg", "jpeg_bytes": b"a"}]
        cleanup_called = {"n": 0}

        async def fake_to_thread(fn, *args):  # noqa: ANN001
            if getattr(fn, "__name__", None) == "delete_slide_artifact_keys_sync":
                cleanup_called["n"] += 1
            return None

        with (
            patch("app.nodes.finalize.get_settings", return_value=settings_mock),
            patch("app.nodes.finalize.post_complete_callback", new_callable=AsyncMock) as post,
            patch("app.nodes.finalize.asyncio.to_thread", new_callable=AsyncMock, side_effect=fake_to_thread),
        ):
            post.return_value = resp
            await finalize(
                _minimal_state(
                    artifacts=artifacts,
                    rendered_slides=rendered,
                    errors=[],
                ),
            )

        first = post.await_args_list[0].kwargs["json_body"]
        self.assertIn("error", first)
        self.assertEqual(first["error"], JOB_FAILURE_HTML_ARTIFACT)
        self.assertEqual(cleanup_called["n"], 1)
