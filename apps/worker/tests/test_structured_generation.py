"""Unit tests for structured generation with a mocked LLM."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from app.structured_generation import StructuredGenerationError, generate_structured_post


def document(post_type="single", asset_id=None):
    elements = [{"id": "title", "type": "text", "role": "heading", "content": "Olá", "style": {"color": "#FFFFFF", "size": "large"}}]
    if asset_id:
        elements.append({"id": "image", "type": "image", "assetId": asset_id, "fit": "cover"})
    return {"schemaVersion": 1, "postType": post_type, "slides": [{"id": "s1", "layout": "hero", "background": {"type": "solid", "color": "#000000"}, "elements": elements}]}


def setup_llm(monkeypatch, outputs):
    calls = []
    class FakeLLM:
        def __init__(self, **kwargs):
            pass
        async def ainvoke(self, messages):
            calls.append(messages)
            return AIMessage(content=outputs[len(calls) - 1])
    monkeypatch.setattr("app.structured_generation.ChatOpenAI", FakeLLM)
    monkeypatch.setattr("app.structured_generation.get_settings", lambda: SimpleNamespace(openai_api_key="test", openai_chat_model="test", generate_slides_max_tokens_cap=4000))
    return calls


def test_valid_single_with_authorized_image(monkeypatch):
    calls = setup_llm(monkeypatch, [json.dumps(document(asset_id="a1"))])
    result = asyncio.run(generate_structured_post(request="Crie", profile_text="Marca", post_type="single", authorized_assets={"a1"}))
    assert result.post_type == "single"
    assert len(calls) == 1


def test_invalid_output_retries_then_succeeds(monkeypatch):
    calls = setup_llm(monkeypatch, ["not json", json.dumps(document("carousel"))])
    result = asyncio.run(generate_structured_post(request="Crie", profile_text="Marca", post_type="carousel", authorized_assets=set(), requested_slide_count=1))
    assert result.post_type == "carousel"
    assert len(calls) == 2
    assert "retryFeedback" in json.loads(calls[1][1].content)


def test_unauthorized_image_fails_after_budget(monkeypatch):
    calls = setup_llm(monkeypatch, [json.dumps(document(asset_id="foreign"))] * 3)
    with pytest.raises(StructuredGenerationError):
        asyncio.run(generate_structured_post(request="Crie", profile_text="Marca", post_type="single", authorized_assets={"a1"}))
    assert len(calls) == 3


def test_wrong_count_fails_after_budget(monkeypatch):
    setup_llm(monkeypatch, [json.dumps(document("carousel"))] * 3)
    with pytest.raises(StructuredGenerationError):
        asyncio.run(generate_structured_post(request="Crie", profile_text="Marca", post_type="carousel", authorized_assets=set(), requested_slide_count=3))
