"""Tests for structured edit planning."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from app.post_document import PostDocumentV1
from app.structured_editing import StructuredEditingError, plan_structured_edit


@pytest.fixture
def document():
    return PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{
        "id": "s1", "layout": "hero", "background": {"type": "solid", "color": "#000000"},
        "elements": [{"id": "title", "type": "text", "role": "heading", "content": "Original", "style": {"color": "#FFFFFF", "size": "large"}}],
    }]})


def fake_llm(monkeypatch, outputs):
    calls = []
    class FakeLLM:
        def __init__(self, **kwargs):
            pass
        async def ainvoke(self, messages):
            calls.append(messages)
            return AIMessage(content=outputs[len(calls) - 1])
    monkeypatch.setattr("app.structured_editing.ChatOpenAI", FakeLLM)
    monkeypatch.setattr("app.structured_editing.get_settings", lambda: SimpleNamespace(openai_api_key="test", openai_chat_model="test", generate_slides_max_tokens_cap=4000))
    return calls


def test_valid_edit_preserves_base(monkeypatch, document):
    fake_llm(monkeypatch, [json.dumps({"status": "ok", "operations": [{"op": "set_background", "slideId": "s1", "background": {"type": "solid", "color": "#123456"}}]})])
    result = asyncio.run(plan_structured_edit(request="Mude o fundo", document=document, authorized_assets=set()))
    assert result.slides[0].background.color == "#123456"
    assert document.slides[0].background.color == "#000000"
    assert result.slides[0].elements == document.slides[0].elements


def test_invalid_plan_retries_then_succeeds(monkeypatch, document):
    calls = fake_llm(monkeypatch, ["invalid", json.dumps({"status": "ok", "operations": [{"op": "set_layout", "slideId": "s1", "layout": "quote"}]})])
    result = asyncio.run(plan_structured_edit(request="Mude o layout", document=document, authorized_assets=set()))
    assert result.slides[0].layout == "quote"
    assert len(calls) == 2
    assert "retryFeedback" in json.loads(calls[1][1].content)


def test_unsupported_request_fails_without_retry(monkeypatch, document):
    calls = fake_llm(monkeypatch, [json.dumps({"status": "unsupported", "operations": []})])
    with pytest.raises(StructuredEditingError, match="Reformule"):
        asyncio.run(plan_structured_edit(request="algo vago", document=document, authorized_assets=set()))
    assert len(calls) == 1


def test_invalid_target_fails_after_budget(monkeypatch, document):
    calls = fake_llm(monkeypatch, [json.dumps({"status": "ok", "operations": [{"op": "set_layout", "slideId": "missing", "layout": "hero"}]})] * 3)
    with pytest.raises(StructuredEditingError):
        asyncio.run(plan_structured_edit(request="edite", document=document, authorized_assets=set()))
    assert len(calls) == 3
