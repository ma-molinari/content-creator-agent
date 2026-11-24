import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from app.post_document_v3 import PostDocumentV3
from app.structured_editing import StructuredEditingError
from app.structured_editing_v3 import plan_content_edit_v3
from app.post_renderer_v3 import render_post_v3
from tests.test_post_document_v3 import document


def mock_llm(monkeypatch, output):
    class FakeLLM:
        def __init__(self, **kwargs): pass
        async def ainvoke(self, messages): return AIMessage(content=json.dumps(output))
    monkeypatch.setattr("app.structured_editing_v3.ChatOpenAI", FakeLLM)
    monkeypatch.setattr("app.structured_editing_v3.get_settings", lambda: SimpleNamespace(openai_api_key="test", openai_chat_model="test", generate_slides_max_tokens_cap=4000))


@pytest.mark.asyncio
async def test_content_edit_preserves_background(monkeypatch):
    mock_llm(monkeypatch, {"status": "ok", "operations": [{"op": "set_text", "slideId": "s1", "elementId": "t1", "content": "Novo"}]})
    original = PostDocumentV3.model_validate(document())
    edited = await plan_content_edit_v3(request="Mude o título", document=original, authorized_assets={"photo"}, image_action=False)
    assert edited.slides[0].elements[0].content == "Novo"
    assert edited.slides[0].background == original.slides[0].background
    assert edited.credits == original.credits


@pytest.mark.asyncio
async def test_unsupported_mixed_edit_is_not_partially_applied(monkeypatch):
    mock_llm(monkeypatch, {"status": "unsupported", "operations": []})
    original = PostDocumentV3.model_validate(document())
    with pytest.raises(StructuredEditingError):
        await plan_content_edit_v3(request="Troque a foto e altere algo impossível", document=original, authorized_assets={"photo"}, image_action=True)
    assert original.slides[0].background.asset_id == "photo"


@pytest.mark.asyncio
async def test_dark_blue_even_slides_adjust_text_and_preserve_other_slides(monkeypatch):
    raw = document()
    raw["postType"] = "carousel"
    raw["credits"] = {}
    raw["slides"] = [dict(raw["slides"][0], id=f"s{i}", background={"type": "solid", "color": {"token": "background"}}) for i in range(1, 9)]
    original = PostDocumentV3.model_validate(raw)
    before = original.model_dump_json(by_alias=True)
    operations = [{"op": "set_background", "slideId": f"s{i}", "background": {"type": "solid", "color": {"hex": "#003366"}}} for i in (2, 4, 6, 8)]
    mock_llm(monkeypatch, {"status": "ok", "operations": operations})
    edited = await plan_content_edit_v3(request="Fundo azul nos cards pares", document=original, authorized_assets=set(), image_action=False)
    assert original.model_dump_json(by_alias=True) == before
    for i, slide in enumerate(edited.slides, 1):
        if i % 2 == 0:
            assert slide.background.color.hex == "#003366"
            assert slide.elements[0].style.color.hex == "#FFFFFF"
        else:
            assert slide == original.slides[i - 1]
    assert len(render_post_v3(edited, set())) == 8


@pytest.mark.asyncio
async def test_readable_text_color_is_preserved(monkeypatch):
    raw = document()
    raw["slides"][0]["background"] = {"type": "solid", "color": {"token": "background"}}
    raw["credits"] = {}
    original = PostDocumentV3.model_validate(raw)
    mock_llm(monkeypatch, {"status": "ok", "operations": [{"op": "set_background", "slideId": "s1", "background": {"type": "solid", "color": {"hex": "#DCEBFF"}}}]})
    edited = await plan_content_edit_v3(request="Fundo azul claro", document=original, authorized_assets=set(), image_action=False)
    assert edited.slides[0].elements[0].style == original.slides[0].elements[0].style
    render_post_v3(edited, set())
