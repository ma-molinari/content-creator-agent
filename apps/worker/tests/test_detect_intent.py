"""Unit tests for detect_intent (S3 HTML load, refinement vs new-generation routing)."""

from __future__ import annotations

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from app.nodes.detect_intent import _infer_refinement_scope, detect_intent
from app.nodes.finalize_messages import JOB_FAILURE_REFINEMENT_CONTEXT
from app.state import SlideItem


def _state(**kwargs: object) -> dict:
    base: dict = {
        "job_id": "job-99",
        "raw_message": "",
        "errors": [],
        "existing_slide_html_s3_keys": [],
        "expects_slide_refinement": False,
    }
    base.update(kwargs)
    return base


class TestDetectIntent(IsolatedAsyncioTestCase):
    def _patch_settings_and_fetch(self, fetch_ret: list[SlideItem]) -> tuple[MagicMock, AsyncMock]:
        settings_mock = MagicMock()
        fetch_mock = AsyncMock(return_value=fetch_ret)
        return settings_mock, fetch_mock

    async def test_no_expects_empty_keys_not_refinement_no_blocked_flag(self) -> None:
        settings_mock, fetch_mock = self._patch_settings_and_fetch([])
        state = _state(expects_slide_refinement=False, existing_slide_html_s3_keys=[])

        with (
            patch("app.nodes.detect_intent.get_settings", return_value=settings_mock),
            patch("app.nodes.detect_intent._fetch_html_slides", fetch_mock),
        ):
            out = await detect_intent(state)  # type: ignore[arg-type]

        fetch_mock.assert_not_called()
        self.assertFalse(out.get("is_refinement"))
        self.assertEqual(out.get("existing_slide_html"), [])
        self.assertNotIn("refinement_context_unavailable", out)

    async def test_no_expects_keys_ok_refinement_with_scope_and_count(self) -> None:
        raw = "Por favor muda o texto do slide."
        slides: list[SlideItem] = [
            {"filename": "slide_01.html", "html": "<html></html>"},
        ]
        keys = ["slides/job/slide_01.html"]
        state = _state(
            expects_slide_refinement=False,
            existing_slide_html_s3_keys=keys,
            raw_message=raw,
        )
        settings_mock, fetch_mock = self._patch_settings_and_fetch(slides)

        with (
            patch("app.nodes.detect_intent.get_settings", return_value=settings_mock),
            patch("app.nodes.detect_intent._fetch_html_slides", fetch_mock),
        ):
            out = await detect_intent(state)  # type: ignore[arg-type]

        fetch_mock.assert_awaited_once()
        self.assertTrue(out.get("is_refinement"))
        self.assertEqual(out.get("requested_slide_count"), 1)
        self.assertEqual(out.get("refinement_scope"), _infer_refinement_scope(raw))
        self.assertEqual(out.get("existing_slide_html"), slides)

    async def test_expects_true_no_keys_blocked_with_refinement_error(self) -> None:
        settings_mock, fetch_mock = self._patch_settings_and_fetch([])
        state = _state(expects_slide_refinement=True, existing_slide_html_s3_keys=[])

        with (
            patch("app.nodes.detect_intent.get_settings", return_value=settings_mock),
            patch("app.nodes.detect_intent._fetch_html_slides", fetch_mock),
        ):
            out = await detect_intent(state)  # type: ignore[arg-type]

        fetch_mock.assert_not_called()
        self.assertFalse(out.get("is_refinement"))
        self.assertTrue(out.get("refinement_context_unavailable"))
        errs = list(out.get("errors") or [])
        self.assertIn(JOB_FAILURE_REFINEMENT_CONTEXT, errs)

    async def test_expects_true_fetch_failure_blocked(self) -> None:
        keys = ["slides/job/slide_01.html"]
        state = _state(
            expects_slide_refinement=True,
            existing_slide_html_s3_keys=keys,
        )
        settings_mock, fetch_mock = self._patch_settings_and_fetch([])

        with (
            patch("app.nodes.detect_intent.get_settings", return_value=settings_mock),
            patch("app.nodes.detect_intent._fetch_html_slides", fetch_mock),
        ):
            out = await detect_intent(state)  # type: ignore[arg-type]

        self.assertFalse(out.get("is_refinement"))
        self.assertTrue(out.get("refinement_context_unavailable"))
        errs = list(out.get("errors") or [])
        self.assertIn(JOB_FAILURE_REFINEMENT_CONTEXT, errs)

    async def test_no_expects_fetch_failure_silent_degradation(self) -> None:
        keys = ["slides/job/slide_01.html"]
        state = _state(
            expects_slide_refinement=False,
            existing_slide_html_s3_keys=keys,
        )
        settings_mock, fetch_mock = self._patch_settings_and_fetch([])

        with (
            patch("app.nodes.detect_intent.get_settings", return_value=settings_mock),
            patch("app.nodes.detect_intent._fetch_html_slides", fetch_mock),
        ):
            out = await detect_intent(state)  # type: ignore[arg-type]

        self.assertFalse(out.get("is_refinement"))
        self.assertEqual(out.get("existing_slide_html"), [])
        self.assertNotIn("refinement_context_unavailable", out)
        errs = list(out.get("errors") or [])
        self.assertNotIn(JOB_FAILURE_REFINEMENT_CONTEXT, errs)


if __name__ == "__main__":
    import unittest

    unittest.main()
