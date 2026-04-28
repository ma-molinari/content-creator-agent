"""Tests for api_client retry helper."""

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

import httpx

from app.api_client import post_complete_callback


class TestPostCompleteCallback(IsolatedAsyncioTestCase):
    async def test_success_first_try(self) -> None:
        ok = httpx.Response(200)
        with patch("app.api_client.httpx.AsyncClient") as ac:
            mock_client = AsyncMock()
            ac.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(return_value=ok)

            out = await post_complete_callback(
                "http://api/internal/jobs/x/complete",
                json_body={"a": 1},
                headers={"X-Worker-API-Key": "k"},
            )

            self.assertEqual(out.status_code, 200)
            mock_client.post.assert_called_once()

    async def test_retries_connect_error_then_success(self) -> None:
        ok = httpx.Response(200)
        with patch("app.api_client.httpx.AsyncClient") as ac:
            mock_client = AsyncMock()
            ac.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(
                side_effect=[
                    httpx.ConnectError("boom"),
                    ok,
                ]
            )

            with patch("app.api_client.asyncio.sleep", new_callable=AsyncMock):
                out = await post_complete_callback(
                    "http://api/internal/jobs/x/complete",
                    json_body={"error": "x"},
                    headers={"h": "v"},
                    attempts=5,
                )

            self.assertEqual(out.status_code, 200)
            self.assertEqual(mock_client.post.await_count, 2)

    async def test_retries_5xx_then_success(self) -> None:
        bad = httpx.Response(503)
        ok = httpx.Response(200)
        with patch("app.api_client.httpx.AsyncClient") as ac:
            mock_client = AsyncMock()
            ac.return_value.__aenter__.return_value = mock_client
            mock_client.post = AsyncMock(side_effect=[bad, ok])

            with patch("app.api_client.asyncio.sleep", new_callable=AsyncMock):
                out = await post_complete_callback(
                    "http://api/internal/jobs/x/complete",
                    json_body={"a": 1},
                    headers=None,
                )

            self.assertEqual(out.status_code, 200)
            self.assertEqual(mock_client.post.await_count, 2)
