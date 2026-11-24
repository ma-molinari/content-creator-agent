import httpx
import pytest
from unittest.mock import AsyncMock
from types import SimpleNamespace
from langchain_core.messages import AIMessage

from app.openverse import ImageSearchError
from app.stock_selection import _plain_credit, select_stock_image


def response(request):
    if request.url.host == "api.openverse.org":
        photo = {"id": "123", "title": "Praia", "creator": "Ana", "license": "cc0",
                 "url": "https://upload.wikimedia.org/wikipedia/a.jpg", "foreign_landing_url": "https://commons.wikimedia.org/a",
                 "license_url": "https://creativecommons.org/publicdomain/zero/1.0/"}
        return httpx.Response(200, json={"results": [photo]})
    return httpx.Response(200, content=b"\xff\xd8\xffimage")


@pytest.mark.asyncio
async def test_selection_keeps_original_credit_and_image_bytes(monkeypatch):
    monkeypatch.setattr("app.stock_selection._choose_photo", AsyncMock(return_value=0))
    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        selected = await select_stock_image("praia", client=client)
    assert selected.asset_id.startswith("stock_")
    assert selected.content.startswith(b"\xff\xd8\xff")
    assert selected.credit.creator == "Ana"
    assert selected.credit.source_url == "https://commons.wikimedia.org/a"


@pytest.mark.asyncio
async def test_selection_never_reuses_excluded_source():
    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        with pytest.raises(ImageSearchError):
            await select_stock_image("praia", client=client, exclude_sources=frozenset({"https://commons.wikimedia.org/a"}))


def test_credits_strip_markup_and_hidden_metadata():
    assert _plain_credit('<div>Fotografia <b>de café</b><span style="display: none">metadado</span><script>ruim()</script></div>') == 'Fotografia de café'


@pytest.mark.asyncio
async def test_vision_chooses_photo_instead_of_first_painting(monkeypatch):
    from app.openverse import ImageCandidate
    from app.stock_selection import _choose_photo
    captured = []
    class FakeLLM:
        def __init__(self, **kwargs): pass
        async def ainvoke(self, messages):
            captured.extend(messages)
            return AIMessage(content='{"index":1}')
    monkeypatch.setattr("app.stock_selection.ChatOpenAI", FakeLLM)
    monkeypatch.setattr("app.stock_selection.get_settings", lambda: SimpleNamespace(openai_api_key="test", reference_vision_model="test"))
    candidate = ImageCandidate("a", "café", "https://upload.wikimedia.org/wikipedia/a.jpg", "https://example.org/a", None, None, "cc0", "https://creativecommons.org/publicdomain/zero/1.0/")
    assert await _choose_photo("coffee", [(candidate, b"\xff\xd8\xfffirst"), (candidate, b"\xff\xd8\xffsecond")]) == 1
    assert len([block for block in captured[1].content if block["type"] == "image_url"]) == 2


@pytest.mark.asyncio
async def test_vision_rejects_when_no_photograph_matches(monkeypatch):
    from app.openverse import ImageCandidate
    from app.stock_selection import _choose_photo
    class FakeLLM:
        def __init__(self, **kwargs): pass
        async def ainvoke(self, messages): return AIMessage(content='{"index":null}')
    monkeypatch.setattr("app.stock_selection.ChatOpenAI", FakeLLM)
    monkeypatch.setattr("app.stock_selection.get_settings", lambda: SimpleNamespace(openai_api_key="test", reference_vision_model="test"))
    candidate = ImageCandidate("a", "pintura", "https://upload.wikimedia.org/wikipedia/a.jpg", "https://example.org/a", None, None, "cc0", "https://creativecommons.org/publicdomain/zero/1.0/")
    assert await _choose_photo("coffee", [(candidate, b"\xff\xd8\xffimage")]) is None


@pytest.mark.asyncio
async def test_selection_tries_next_batch_when_first_is_not_relevant(monkeypatch):
    def many(request):
        if request.url.host != "api.openverse.org":
            return httpx.Response(200, content=b"\xff\xd8\xffimage")
        photos = [{"id": str(i), "title": f"Foto {i}", "license": "cc0",
                   "url": f"https://upload.wikimedia.org/wikipedia/{i}.jpg",
                   "foreign_landing_url": f"https://commons.wikimedia.org/{i}",
                   "license_url": "https://creativecommons.org/publicdomain/zero/1.0/"} for i in range(6)]
        return httpx.Response(200, json={"results": photos})
    choose = AsyncMock(side_effect=[None, 0])
    monkeypatch.setattr("app.stock_selection._choose_photo", choose)
    async with httpx.AsyncClient(transport=httpx.MockTransport(many)) as client:
        selected = await select_stock_image("café", client=client)
    assert selected.credit.source_url == "https://commons.wikimedia.org/5"
    assert choose.await_count == 2
