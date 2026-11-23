"""V2 planners receive only the intended direction and preserve the base."""

import asyncio
import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from app.post_document_v2 import PostDocumentV2
from app.structured_editing import StructuredEditingError, plan_structured_edit_v2
from app.structured_generation import StructuredGenerationError, generate_structured_post_v2
from app.visual_direction import VisualDirection


def raw_document():
    return {"schemaVersion": 2, "postType": "single", "palette": {"background": "#FFFFFF", "text": "#000000", "accent": "#F26930"},
            "slides": [{"id": "s1", "layout": "hero", "background": {"type": "solid", "color": {"token": "background"}},
                        "elements": [{"id": "title", "type": "text", "role": "heading", "content": "Original",
                                      "style": {"color": {"token": "text"}, "size": "large"}}]}]}


def direction():
    return VisualDirection.model_validate({"palette": {"background": {"status": "observed", "value": "#FFFFFF"},
        "text": {"status": "observed", "value": "#000000"}, "accent": {"status": "observed", "value": "#F26930"}},
        "decorations": [{"status": "observed", "kind": "bar", "position": "top", "color": "#F26930"}]})


def fake(monkeypatch, target, outputs):
    calls = []
    class LLM:
        def __init__(self, **kwargs): pass
        async def ainvoke(self, messages):
            calls.append(messages)
            return AIMessage(content=outputs[len(calls) - 1])
    monkeypatch.setattr(target + ".ChatOpenAI", LLM)
    monkeypatch.setattr(target + ".get_settings", lambda: SimpleNamespace(openai_api_key="secret-not-in-payload", openai_chat_model="test", generate_slides_max_tokens_cap=4000))
    return calls


def test_create_with_observed_bar_and_validated_direction(monkeypatch):
    raw = raw_document()
    raw["slides"][0]["elements"].insert(0, {"id": "bar", "type": "decoration", "kind": "bar", "color": {"token": "accent"}, "width": "full", "thickness": "medium", "corner": "rounded"})
    calls = fake(monkeypatch, "app.structured_generation", [json.dumps(raw)])
    result = asyncio.run(generate_structured_post_v2(request="Criar", profile_text="perfil", post_type="single", authorized_assets=set(), visual_direction=direction()))
    payload = json.loads(calls[0][1].content)
    assert payload["visualDirection"]["decorations"][0]["position"] == "top"
    assert result.slides[0].elements[0].kind == "bar"
    assert "secret-not-in-payload" not in calls[0][1].content
    assert "corner deve ser square" in calls[0][0].content


def test_generation_retries_unauthorized_asset_then_fails(monkeypatch):
    raw = raw_document()
    raw["slides"][0]["elements"] = [{"id": "i", "type": "image", "assetId": "foreign", "fit": "cover"}]
    calls = fake(monkeypatch, "app.structured_generation", [json.dumps(raw)] * 3)
    with pytest.raises(StructuredGenerationError):
        asyncio.run(generate_structured_post_v2(request="Criar", profile_text="", post_type="single", authorized_assets=set()))
    assert len(calls) == 3
    assert json.loads(calls[0][1].content)["visualDirection"] is None


def test_generation_retries_low_contrast_with_safe_feedback(monkeypatch):
    invalid = raw_document()
    invalid["palette"]["text"] = "#CCCCCC"
    valid = raw_document()
    calls = fake(monkeypatch, "app.structured_generation", [json.dumps(invalid), json.dumps(valid)])
    result = asyncio.run(generate_structured_post_v2(request="Criar", profile_text="", post_type="single", authorized_assets=set()))
    assert result.palette.text == "#000000"
    assert len(calls) == 2
    assert "4,5:1" in json.loads(calls[1][1].content)["retryFeedback"]


def test_edit_with_direction_and_ordinary_edit_without_direction(monkeypatch):
    base = PostDocumentV2.model_validate(raw_document())
    operation = {"op": "insert_decoration", "slideId": "s1", "afterElementId": None,
                 "decoration": {"id": "bar", "type": "decoration", "kind": "bar", "color": {"token": "accent"}, "width": "full", "thickness": "medium", "corner": "rounded"}}
    calls = fake(monkeypatch, "app.structured_editing", [json.dumps({"status": "ok", "operations": [operation]})])
    result = asyncio.run(plan_structured_edit_v2(request="Aplique as referências", document=base, authorized_assets=set(), reapply_references=True, visual_direction=direction()))
    assert result.slides[0].elements[0].id == "bar" and base.slides[0].elements[0].id == "title"
    assert "visualDirection" in json.loads(calls[0][1].content)
    calls = fake(monkeypatch, "app.structured_editing", [json.dumps({"status": "ok", "operations": [{"op": "set_text", "slideId": "s1", "elementId": "title", "content": "Novo"}]})])
    asyncio.run(plan_structured_edit_v2(request="Mude o texto", document=base, authorized_assets=set()))
    assert "visualDirection" not in json.loads(calls[0][1].content)
    with pytest.raises(StructuredEditingError):
        asyncio.run(plan_structured_edit_v2(request="Mude o texto", document=base, authorized_assets=set(), visual_direction=direction()))


def test_unsupported_edit_is_not_retried(monkeypatch):
    calls = fake(monkeypatch, "app.structured_editing", [json.dumps({"status": "unsupported", "operations": []})])
    with pytest.raises(StructuredEditingError, match="Reformule"):
        asyncio.run(plan_structured_edit_v2(request="algo ambíguo", document=PostDocumentV2.model_validate(raw_document()), authorized_assets=set()))
    assert len(calls) == 1
