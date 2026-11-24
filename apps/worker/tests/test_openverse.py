import httpx
import pytest
import logging
from io import StringIO
from unittest.mock import AsyncMock

from app.openverse import ImageCandidate, ImageSearchError, download_image, search_images


@pytest.mark.asyncio
async def test_search_filters_results_and_preserves_provenance():
    def respond(request):
        assert request.url.params["license"] == "cc0"
        assert request.url.params["q"] == "plantas"
        assert request.url.params["source"] == "wikimedia"
        assert request.headers["user-agent"].startswith("PostMind/1.0 (")
        valid = {"id": "abc", "title": "Planta", "url": "https://upload.wikimedia.org/wikipedia/a.jpg",
                 "foreign_landing_url": "https://source.example/a", "creator": "Autora",
                 "creator_url": "https://source.example/author", "license": "cc0",
                 "license_url": "https://creativecommons.org/publicdomain/zero/1.0/"}
        return httpx.Response(200, json={"results": [valid, {**valid, "license": "by-nc"},
                                                       {**valid, "url": "http://localhost/image"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        result = await search_images(" plantas ", client=client)
    assert len(result) == 1
    assert result[0].creator == "Autora"
    assert result[0].source_url == "https://source.example/a"
    assert result[0].license == "cc0"


@pytest.mark.asyncio
async def test_search_fails_safely_on_rate_limit():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(429))) as client:
        with pytest.raises(ImageSearchError):
            await search_images("plantas", client=client)


@pytest.mark.asyncio
async def test_invalid_search_does_not_request_api():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: pytest.fail("unexpected request"))) as client:
        with pytest.raises(ValueError):
            await search_images("", client=client)


@pytest.mark.asyncio
async def test_download_restricts_host_and_checks_image_bytes():
    def candidate(url):
        return ImageCandidate("a", "", url, "https://commons.wikimedia.org/a", None, None,
                              "cc0", "https://creativecommons.org/publicdomain/zero/1.0/")

    def respond(request):
        assert request.headers["user-agent"].startswith("PostMind/1.0 (")
        return httpx.Response(200, content=b"\xff\xd8\xffimage")

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        assert await download_image(candidate("https://upload.wikimedia.org/wikipedia/a.jpg"), client=client) == b"\xff\xd8\xffimage"
        with pytest.raises(ImageSearchError):
            await download_image(candidate("https://evil.example/wikipedia/a.jpg"), client=client)


@pytest.mark.asyncio
async def test_download_rejects_redirect_and_oversized_image():
    candidate = ImageCandidate("a", "", "https://upload.wikimedia.org/wikipedia/a.jpg",
                               "https://commons.wikimedia.org/a", None, None, "cc0",
                               "https://creativecommons.org/publicdomain/zero/1.0/")
    for response in [httpx.Response(302, headers={"Location": "https://evil.example"}),
                     httpx.Response(200, content=b"x" * (5 * 1024 * 1024 + 1))]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: response)) as client:
            with pytest.raises(ImageSearchError):
                await download_image(candidate, client=client)


@pytest.mark.asyncio
@pytest.mark.parametrize(("response", "reason"), [
    (httpx.Response(429), "rate_limit"),
    (httpx.Response(503), "upstream"),
    (httpx.Response(200, json={"results": "invalid"}), "invalid_response"),
])
async def test_search_metrics_are_categorized_without_query(caplog, response, reason):
    caplog.set_level(logging.INFO, logger="app.openverse")
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: response)) as client:
        with pytest.raises(ImageSearchError):
            await search_images("consulta-privada-sentinela", client=client)
    messages = [record.getMessage() for record in caplog.records if record.name == "app.openverse"]
    assert len(messages) == 1
    assert f"event=stock_search outcome=failed reason={reason}" in messages[0]
    assert "sentinela" not in messages[0]
    assert "http" not in messages[0]


@pytest.mark.asyncio
async def test_search_metrics_categorize_timeout(caplog):
    caplog.set_level(logging.INFO, logger="app.openverse")
    client = AsyncMock()
    client.get.side_effect = httpx.ReadTimeout("consulta-privada-sentinela")
    with pytest.raises(ImageSearchError):
        await search_images("consulta-privada-sentinela", client=client)
    messages = [record.getMessage() for record in caplog.records if record.name == "app.openverse"]
    assert len(messages) == 1
    assert "event=stock_search outcome=failed reason=timeout" in messages[0]
    assert "sentinela" not in messages[0]


@pytest.mark.asyncio
async def test_worker_lifespan_suppresses_httpx_url_logs(monkeypatch, caplog):
    from app.main import app, lifespan
    caplog.set_level(logging.INFO)
    httpx_logger = logging.getLogger("httpx")
    httpcore_logger = logging.getLogger("httpcore")
    old_levels = httpx_logger.level, httpcore_logger.level
    sink = StringIO()
    handler = logging.StreamHandler(sink)
    httpx_logger.addHandler(handler)
    monkeypatch.setattr("app.main.asyncio.sleep", AsyncMock())
    try:
        httpx_logger.setLevel(logging.INFO)
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"results": []}))) as client:
            await search_images("consulta-privada-sentinela", client=client)
        assert "consulta-privada-sentinela" in caplog.text
        assert "consulta-privada-sentinela" in sink.getvalue()
        caplog.clear()
        sink.seek(0)
        sink.truncate()
        async with lifespan(app):
            async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"results": []}))) as client:
                await search_images("consulta-privada-sentinela", client=client)
        assert "event=stock_search outcome=success reason=ok" in caplog.text
        assert "consulta-privada-sentinela" not in caplog.text
        assert "api.openverse.org" not in caplog.text
        assert "consulta-privada-sentinela" not in sink.getvalue()
    finally:
        httpx_logger.removeHandler(handler)
        httpx_logger.setLevel(old_levels[0])
        httpcore_logger.setLevel(old_levels[1])
