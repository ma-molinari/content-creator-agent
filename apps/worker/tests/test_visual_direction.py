"""Visual extraction is complete, bounded, isolated, and does not log content."""

import asyncio
import json
import logging
from types import SimpleNamespace

import pytest

from app import visual_direction as module


def valid():
    return {"palette": {"background": {"status": "observed", "value": "#FFFFFF"},
                        "text": {"status": "uncertain", "value": None},
                        "accent": {"status": "absent", "value": None}},
            "decorations": [{"status": "observed", "kind": "bar", "position": "top", "color": "#FF0000"}]}


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    module._cache.clear()
    settings = SimpleNamespace(aws_region="region", aws_access_key_id="key", aws_secret_access_key="secret",
                               aws_s3_bucket="bucket", reference_image_max_bytes=1024,
                               reference_vision_model="vision-model", openai_api_key="key", openai_chat_model="chat-model")
    monkeypatch.setattr(module, "get_settings", lambda: settings)
    monkeypatch.setattr(module.boto3, "client", lambda *args, **kwargs: object())
    monkeypatch.setattr(module, "fetch_bytes_limited", lambda _client, _bucket, key, _limit: key.encode())
    monkeypatch.setattr(module, "guess_mime", lambda _raw, _key: "image/png")
    yield
    module._cache.clear()


def test_cache_is_user_image_order_and_model_scoped(monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    calls = []
    class LLM:
        def __init__(self, **kwargs): calls.append(kwargs["model"])
        async def ainvoke(self, _messages): return SimpleNamespace(content=json.dumps(valid()))
    monkeypatch.setattr(module, "ChatOpenAI", LLM)
    def run(user, keys):
        return asyncio.run(module.extract_visual_direction(user_id=user, reference_keys=keys))
    assert run("user-1", ["private-reference-a", "b"]) == run("user-1", ["private-reference-a", "b"])
    run("user-2", ["private-reference-a", "b"])
    run("user-1", ["b", "private-reference-a"])
    assert len(calls) == 3
    assert "private-reference-a" not in caplog.text
    assert "event=visual_direction" in caplog.text
    assert all("user-1" not in key and "private-reference-a" not in key for key in module._cache)


def test_invalid_output_retries_and_never_caches_failures(monkeypatch):
    calls = []
    class LLM:
        def __init__(self, **_kwargs): pass
        async def ainvoke(self, _messages):
            calls.append(1)
            return SimpleNamespace(content='{"incomplete":true}')
    monkeypatch.setattr(module, "ChatOpenAI", LLM)
    with pytest.raises(module.VisualDirectionError):
        asyncio.run(module.extract_visual_direction(user_id="u", reference_keys=["a"]))
    assert len(calls) == 3 and not module._cache


def test_partial_fetch_and_limits_fail_clearly(monkeypatch):
    def fetch(_client, _bucket, key, _limit):
        if key == "fail": raise RuntimeError("private details")
        return b"image"
    monkeypatch.setattr(module, "fetch_bytes_limited", fetch)
    with pytest.raises(module.VisualDirectionError, match="todas"):
        asyncio.run(module.extract_visual_direction(user_id="u", reference_keys=["ok", "fail"]))
    with pytest.raises(module.VisualDirectionError, match="oito"):
        asyncio.run(module.extract_visual_direction(user_id="u", reference_keys=["x"] * 9))
    assert asyncio.run(module.extract_visual_direction(user_id="u", reference_keys=[])) is None
    with pytest.raises(module.VisualDirectionError, match="Adicione"):
        asyncio.run(module.extract_visual_direction(user_id="u", reference_keys=[], reapply=True))
    assert not module._cache


def test_expiration_and_capacity(monkeypatch):
    now = [0.0]
    monkeypatch.setattr(module, "monotonic", lambda: now[0])
    monkeypatch.setattr(module, "_MAX_CACHE", 2)
    class LLM:
        def __init__(self, **_kwargs): pass
        async def ainvoke(self, _messages): return SimpleNamespace(content=json.dumps(valid()))
    monkeypatch.setattr(module, "ChatOpenAI", LLM)
    for key in ["a", "b", "c"]:
        asyncio.run(module.extract_visual_direction(user_id="u", reference_keys=[key]))
    assert len(module._cache) == 2
    now[0] = 3601
    asyncio.run(module.extract_visual_direction(user_id="u", reference_keys=["d"]))
    assert len(module._cache) == 1


def test_ambiguous_color_must_not_claim_an_observed_value():
    data = valid()
    data["palette"]["text"]["value"] = "#FFFFFF"
    with pytest.raises(ValueError):
        module.VisualDirection.model_validate(data)


@pytest.mark.parametrize("decision,expected", [("yes", True), ("no", False), ("uncertain", None)])
def test_reference_reapplication_requires_unambiguous_decision(monkeypatch, decision, expected):
    class LLM:
        def __init__(self, **_kwargs): pass
        async def ainvoke(self, _messages): return SimpleNamespace(content=json.dumps({"decision": decision}))
    monkeypatch.setattr(module, "ChatOpenAI", LLM)
    if expected is None:
        with pytest.raises(module.VisualDirectionError, match="Reformule"):
            asyncio.run(module.requests_reference_reapplication("pedido ambíguo"))
    else:
        assert asyncio.run(module.requests_reference_reapplication("pedido")) is expected
