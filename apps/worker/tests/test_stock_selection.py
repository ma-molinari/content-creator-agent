import httpx
import pytest
import logging
from unittest.mock import AsyncMock
from types import SimpleNamespace
from langchain_core.messages import AIMessage

from app.openverse import ImageSearchError
from app.stock_selection import PhotoChoice, _plain_credit, select_stock_image


def choice(index=0):
    return PhotoChoice.model_validate({"index": index, "focalBox": {"left": 20, "top": 10, "right": 80, "bottom": 60}})


def response(request):
    if request.url.host == "api.openverse.org":
        photo = {"id": "123", "title": "Praia", "creator": "Ana", "license": "cc0",
                 "url": "https://upload.wikimedia.org/wikipedia/a.jpg", "foreign_landing_url": "https://commons.wikimedia.org/a",
                 "license_url": "https://creativecommons.org/publicdomain/zero/1.0/"}
        return httpx.Response(200, json={"results": [photo]})
    return httpx.Response(200, content=b"\xff\xd8\xffimage")


@pytest.mark.asyncio
async def test_selection_keeps_original_credit_and_image_bytes(monkeypatch):
    monkeypatch.setattr("app.stock_selection._choose_photo", AsyncMock(return_value=choice()))
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
            return AIMessage(content='{"index":1,"focalBox":{"left":20,"top":10,"right":80,"bottom":60}}')
    monkeypatch.setattr("app.stock_selection.ChatOpenAI", FakeLLM)
    monkeypatch.setattr("app.stock_selection.get_settings", lambda: SimpleNamespace(openai_api_key="test", reference_vision_model="test"))
    candidate = ImageCandidate("a", "café", "https://upload.wikimedia.org/wikipedia/a.jpg", "https://example.org/a", None, None, "cc0", "https://creativecommons.org/publicdomain/zero/1.0/")
    selected = await _choose_photo("coffee", [(candidate, b"\xff\xd8\xfffirst"), (candidate, b"\xff\xd8\xffsecond")])
    assert selected.index == 1
    assert selected.focal_box.top == 10
    assert len([block for block in captured[1].content if block["type"] == "image_url"]) == 2


@pytest.mark.asyncio
async def test_vision_rejects_when_no_photograph_matches(monkeypatch):
    from app.openverse import ImageCandidate
    from app.stock_selection import _choose_photo
    class FakeLLM:
        def __init__(self, **kwargs): pass
        async def ainvoke(self, messages): return AIMessage(content='{"index":null,"focalBox":null}')
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
    choose = AsyncMock(side_effect=[None, choice()])
    monkeypatch.setattr("app.stock_selection._choose_photo", choose)
    async with httpx.AsyncClient(transport=httpx.MockTransport(many)) as client:
        selected = await select_stock_image("café", client=client)
    assert selected.credit.source_url == "https://commons.wikimedia.org/5"
    assert choose.await_count == 2


@pytest.mark.asyncio
async def test_selection_metrics_report_outcomes_without_private_data(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="app.stock_selection")
    choose = AsyncMock(return_value=choice())
    monkeypatch.setattr("app.stock_selection._choose_photo", choose)
    async with httpx.AsyncClient(transport=httpx.MockTransport(response)) as client:
        await select_stock_image("consulta-privada-sentinela", client=client)
        choose.return_value = None
        with pytest.raises(ImageSearchError):
            await select_stock_image("consulta-privada-sentinela", client=client)
        choose.side_effect = ImageSearchError("erro-privado-sentinela")
        with pytest.raises(ImageSearchError):
            await select_stock_image("consulta-privada-sentinela", client=client)
    messages = [record.getMessage() for record in caplog.records if record.name == "app.stock_selection"]
    assert len(messages) == 3
    assert "event=stock_selection outcome=success reason=ok" in messages[0]
    assert "event=stock_selection outcome=failed reason=no_candidate" in messages[1]
    assert "event=stock_selection outcome=failed reason=vision" in messages[2]
    assert all("sentinela" not in message and "http" not in message and "Praia" not in message for message in messages)


@pytest.mark.asyncio
async def test_selection_metrics_distinguish_search_and_download_failure(caplog):
    caplog.set_level(logging.INFO, logger="app.stock_selection")
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(503))) as client:
        with pytest.raises(ImageSearchError):
            await select_stock_image("sentinela", client=client)

    def download_fails(request):
        return response(request) if request.url.host == "api.openverse.org" else httpx.Response(503)

    async with httpx.AsyncClient(transport=httpx.MockTransport(download_fails)) as client:
        with pytest.raises(ImageSearchError):
            await select_stock_image("sentinela", client=client)
    messages = [record.getMessage() for record in caplog.records if record.name == "app.stock_selection"]
    assert len(messages) == 2
    assert "outcome=failed reason=search" in messages[0]
    assert "outcome=failed reason=download" in messages[1]
    assert all("sentinela" not in message and "http" not in message for message in messages)
