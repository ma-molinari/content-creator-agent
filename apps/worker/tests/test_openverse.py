import httpx
import pytest

from app.openverse import ImageCandidate, ImageSearchError, download_image, search_images


@pytest.mark.asyncio
async def test_search_filters_results_and_preserves_provenance():
    def respond(request):
        assert request.url.params["license"] == "cc0"
        assert request.url.params["q"] == "plantas"
        assert request.url.params["source"] == "wikimedia"
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

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"\xff\xd8\xffimage"))) as client:
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
