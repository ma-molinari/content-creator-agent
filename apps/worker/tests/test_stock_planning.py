import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

from app.stock_planning import plan_stock_action


@pytest.mark.asyncio
async def test_text_only_edit_does_not_search_or_call_llm(monkeypatch):
    monkeypatch.setattr("app.stock_planning.get_settings", lambda: pytest.fail("unexpected LLM call"))
    plan = await plan_stock_action(request="Altere apenas o título", mode="edit", slide_count=1)
    assert plan.action == "none"


@pytest.mark.asyncio
async def test_planning_retries_out_of_range_slide(monkeypatch):
    responses = iter([{"action": "replace", "query": "floresta", "slide_number": 3},
                      {"action": "replace", "query": "floresta", "slide_number": 1}])

    class FakeLLM:
        def __init__(self, **kwargs): pass
        async def ainvoke(self, messages): return AIMessage(content=json.dumps(next(responses)))

    monkeypatch.setattr("app.stock_planning.ChatOpenAI", FakeLLM)
    monkeypatch.setattr("app.stock_planning.get_settings", lambda: SimpleNamespace(openai_api_key="test", openai_chat_model="test"))
    plan = await plan_stock_action(request="troque a imagem", mode="edit", slide_count=1)
    assert plan.query == "floresta"
    assert plan.slide_number == 1
