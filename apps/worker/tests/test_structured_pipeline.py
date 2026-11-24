"""Integration-oriented tests for the isolated structured pipeline."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.immutable_assets import CopiedAssets
from app.job_payload import DispatchPayload, initial_state
from app.nodes.structured_pipeline import structured_pipeline
from app.post_document import PostDocumentV1
from app.structured_upload import StructuredCallbackUnknown, StructuredUpload
from app.post_document_v2 import promote_v1
from app.reference_policy import ReferenceSelectionError
from app.post_operations import apply_operations
from app.post_operations_v2 import apply_operations_v2


def make_document():
    return PostDocumentV1.model_validate({"schemaVersion": 1, "postType": "single", "slides": [{
        "id": "s", "layout": "hero", "background": {"type": "solid", "color": "#000000"},
        "elements": [{"id": "t", "type": "text", "role": "heading", "content": "Título", "style": {"color": "#FFFFFF", "size": "large"}}],
    }]})


def setup(monkeypatch, *, requirements=None, status=204):
    mod = "app.nodes.structured_pipeline."
    settings = SimpleNamespace(aws_region="test", aws_access_key_id="test", aws_secret_access_key="test", aws_s3_bucket="bucket", go_api_url="http://api", worker_api_key="key")
    monkeypatch.setattr(mod + "get_settings", lambda: settings)
    monkeypatch.setattr(mod + "report_job_progress", AsyncMock())
    monkeypatch.setattr(mod + "attachment_analyze", AsyncMock(return_value={"attachment_plan": requirements or []}))
    monkeypatch.setattr(mod + "boto3.client", lambda *args, **kwargs: MagicMock())
    monkeypatch.setattr(mod + "generate_structured_post", AsyncMock(return_value=make_document()))
    monkeypatch.setattr(mod + "plan_structured_edit", AsyncMock(return_value=make_document()))
    monkeypatch.setattr(mod + "copy_version_assets", AsyncMock(return_value=CopiedAssets({}, {})))
    monkeypatch.setattr(mod + "render_structured_post", AsyncMock(return_value=([{"filename": "slide_01.html", "html": "<html></html>"}], [{"filename": "slide_01.jpeg", "jpeg_bytes": b"\xff\xd8\xff"}])))
    monkeypatch.setattr(mod + "upload_structured_post", AsyncMock(return_value=StructuredUpload("slides/x/document.json", [])))
    callback = AsyncMock(return_value=status)
    monkeypatch.setattr(mod + "send_structured_completion", callback)
    return callback


def test_create_runs_all_stages(monkeypatch):
    callback = setup(monkeypatch)
    payload = DispatchPayload(job_id=uuid4(), user_id=uuid4(), chat_id=uuid4(), post_format="structured_v1", generation_mode="create", chat_post_type="single", raw_message="Crie")
    assert asyncio.run(structured_pipeline(initial_state(payload))) == {}
    assert callback.await_count == 1
    assert callback.await_args.kwargs["assistant_text"] == "Post criado."


@pytest.mark.parametrize("target", [1, 2])
@pytest.mark.parametrize("explicit", [False, True])
def test_creation_exposes_reference_only_when_explicit(monkeypatch, target, explicit):
    callback = setup(monkeypatch)
    mod = "app.nodes.structured_pipeline."
    raw = make_document().model_dump(mode="json", by_alias=True)
    if explicit:
        raw["slides"][0]["elements"].append({"id": "picture", "type": "image", "assetId": "ref-id", "fit": "contain"})
    output = PostDocumentV1.model_validate(raw)
    if target == 2:
        output = promote_v1(output)
        monkeypatch.setattr(mod + "extract_visual_direction", AsyncMock(return_value=None))
    generator = AsyncMock(return_value=output)
    monkeypatch.setattr(mod + ("generate_structured_post_v2" if target == 2 else "generate_structured_post"), generator)
    payload = DispatchPayload(job_id=uuid4(), user_id=uuid4(), chat_id=uuid4(), post_format="structured_v1",
        target_schema_version=target, generation_mode="create", chat_post_type="single",
        raw_message="Inclua a imagem de referência no post" if explicit else "Use a referência como inspiração",
        reference_s3_keys=["ref-key"], reference_asset_sources={"ref-id": "ref-key"},
        authorized_asset_sources={"attachment-id": "attachment-key"})
    asyncio.run(structured_pipeline(initial_state(payload)))
    assert generator.await_args.kwargs["authorized_assets"] == ({"attachment-id", "ref-id"} if explicit else {"attachment-id"})
    assert callback.await_count == 1


@pytest.mark.parametrize("target", [1, 2])
def test_creation_rejects_reference_even_if_generator_ignores_allowlist(monkeypatch, target):
    callback = setup(monkeypatch)
    mod = "app.nodes.structured_pipeline."
    raw = make_document().model_dump(mode="json", by_alias=True)
    raw["slides"][0]["elements"].append({"id": "picture", "type": "image", "assetId": "ref-id", "fit": "contain"})
    output = PostDocumentV1.model_validate(raw)
    if target == 2:
        output = promote_v1(output)
        monkeypatch.setattr(mod + "extract_visual_direction", AsyncMock(return_value=None))
    monkeypatch.setattr(mod + ("generate_structured_post_v2" if target == 2 else "generate_structured_post"), AsyncMock(return_value=output))
    payload = DispatchPayload(job_id=uuid4(), user_id=uuid4(), chat_id=uuid4(), post_format="structured_v1",
        target_schema_version=target, generation_mode="create", chat_post_type="single", raw_message="Crie um post",
        reference_s3_keys=["ref-key"], reference_asset_sources={"ref-id": "ref-key"})
    with pytest.raises(ReferenceSelectionError):
        asyncio.run(structured_pipeline(initial_state(payload)))
    assert callback.await_count == 0


def test_old_api_with_references_fails_closed(monkeypatch):
    callback = setup(monkeypatch)
    payload = DispatchPayload(job_id=uuid4(), user_id=uuid4(), chat_id=uuid4(), post_format="structured_v1",
        generation_mode="create", chat_post_type="single", reference_s3_keys=["ref-key"],
        authorized_asset_sources={"ref-id": "ref-key"})
    with pytest.raises(ReferenceSelectionError, match="Atualize"):
        asyncio.run(structured_pipeline(initial_state(payload)))
    assert callback.await_count == 0


@pytest.mark.parametrize("target", [1, 2])
@pytest.mark.parametrize("explicit", [False, True])
def test_edit_preserves_inherited_image_and_inserts_only_selected_reference(monkeypatch, target, explicit):
    callback = setup(monkeypatch)
    mod = "app.nodes.structured_pipeline."
    raw = make_document().model_dump(mode="json", by_alias=True)
    raw["slides"][0]["elements"].append({"id": "existing", "type": "image", "assetId": "ref-a", "fit": "contain"})
    old = PostDocumentV1.model_validate(raw)
    monkeypatch.setattr(mod + "fetch_bytes_limited", lambda *_args: old.model_dump_json(by_alias=True).encode())
    monkeypatch.setattr(mod + "requests_reference_reapplication", AsyncMock(return_value=False))
    async def planner(**kwargs):
        op = ({"op": "insert_image", "slideId": "s", "afterElementId": "t", "image":
               {"id": "new", "type": "image", "assetId": "ref-b", "fit": "contain"}} if explicit else
              {"op": "set_text", "slideId": "s", "elementId": "t", "content": "Editado"})
        return (apply_operations_v2 if target == 2 else apply_operations)(kwargs["document"], [op], kwargs["authorized_assets"])
    monkeypatch.setattr(mod + ("plan_structured_edit_v2" if target == 2 else "plan_structured_edit"), planner)
    payload = DispatchPayload(job_id=uuid4(), user_id=uuid4(), chat_id=uuid4(), post_format="structured_v1",
        target_schema_version=target, generation_mode="edit", base_version_id=uuid4(),
        document_s3_key=f"slides/{uuid4()}/document.json", chat_post_type="single",
        raw_message="Inclua a segunda imagem de referência no post" if explicit else "Mude apenas o texto",
        reference_s3_keys=["ref-a-key", "ref-b-key"], reference_asset_sources={"ref-a": "ref-a-key", "ref-b": "ref-b-key"},
        authorized_asset_sources={"ref-a": f"slides/{uuid4()}/assets/ref-a.png"})
    copied = AsyncMock(return_value=CopiedAssets({}, {}))
    monkeypatch.setattr(mod + "copy_version_assets", copied)
    asyncio.run(structured_pipeline(initial_state(payload)))
    result = copied.await_args.args[0]
    ids = [item.asset_id for item in result.slides[0].elements if item.type == "image"]
    assert ids == (["ref-b", "ref-a"] if explicit else ["ref-a"])
    assert copied.await_args.kwargs["authorized_sources"]["ref-a"] != "ref-a-key"
    assert callback.await_count == 1


def test_edit_reads_authorized_base(monkeypatch):
    callback = setup(monkeypatch)
    monkeypatch.setattr("app.nodes.structured_pipeline.fetch_bytes_limited", lambda *args: make_document().model_dump_json(by_alias=True).encode())
    payload = DispatchPayload(job_id=uuid4(), user_id=uuid4(), chat_id=uuid4(), post_format="structured_v1", generation_mode="edit", base_version_id=uuid4(), document_s3_key=f"slides/{uuid4()}/document.json", chat_post_type="single", raw_message="Edite")
    asyncio.run(structured_pipeline(initial_state(payload)))
    assert callback.await_args.kwargs["assistant_text"] == "Post atualizado."


def test_required_attachment_missing_prevents_callback(monkeypatch):
    callback = setup(monkeypatch, requirements=[{"id": "image", "required_slide_number": 1}])
    payload = DispatchPayload(job_id=uuid4(), user_id=uuid4(), chat_id=uuid4(), post_format="structured_v1", generation_mode="create", chat_post_type="single")
    with pytest.raises(ValueError, match="required image"):
        asyncio.run(structured_pipeline(initial_state(payload)))
    assert callback.await_count == 0


def test_invalid_contract_does_not_fall_back_to_legacy():
    with pytest.raises(ValidationError):
        DispatchPayload(job_id=uuid4(), user_id=uuid4(), chat_id=uuid4(), post_format="structured_v2")
    with pytest.raises(ValidationError):
        DispatchPayload(job_id=uuid4(), user_id=uuid4(), chat_id=uuid4(), post_format="structured_v1", generation_mode="edit")


def test_unknown_callback_does_not_send_failure(monkeypatch):
    from app.main import _run_job
    graph = SimpleNamespace(ainvoke=AsyncMock(side_effect=StructuredCallbackUnknown("unknown")))
    failure = AsyncMock()
    monkeypatch.setattr("app.main.graph", graph)
    monkeypatch.setattr("app.main.report_job_failure", failure)
    asyncio.run(_run_job({"job_id": str(uuid4())}))
    assert failure.await_count == 0


def test_unsupported_edit_reports_safe_error_code(monkeypatch):
    from app.main import _run_job
    from app.structured_editing import StructuredEditingError
    graph = SimpleNamespace(ainvoke=AsyncMock(side_effect=StructuredEditingError("private")))
    failure = AsyncMock()
    monkeypatch.setattr("app.main.graph", graph)
    monkeypatch.setattr("app.main.report_job_failure", failure)
    asyncio.run(_run_job({"job_id": str(uuid4()), "post_format": "structured_v1"}))
    assert failure.await_args.kwargs["error_code"] == "EDIT_UNSUPPORTED"
    assert "private" not in failure.await_args.args[1]


def test_stock_planning_reports_safe_error_code(monkeypatch):
    from app.main import _run_job
    from app.stock_planning import StockPlanningError
    graph = SimpleNamespace(ainvoke=AsyncMock(side_effect=StockPlanningError("private")))
    failure = AsyncMock()
    monkeypatch.setattr("app.main.graph", graph)
    monkeypatch.setattr("app.main.report_job_failure", failure)
    asyncio.run(_run_job({"job_id": str(uuid4()), "post_format": "structured_v1", "target_schema_version": 3}))
    assert failure.await_args.kwargs["error_code"] == "EDIT_UNSUPPORTED"
    assert "private" not in failure.await_args.args[1]


def test_runtime_graph_preserves_legacy_route(monkeypatch):
    from app.graph import build_graph

    structured = AsyncMock(return_value={})
    legacy_intent = AsyncMock(return_value={"refinement_context_unavailable": True})
    finalize = AsyncMock(return_value={})
    monkeypatch.setattr("app.graph.report_job_progress", AsyncMock())
    monkeypatch.setattr("app.graph.structured_pipeline", structured)
    monkeypatch.setattr("app.graph.intent_detect", legacy_intent)
    monkeypatch.setattr("app.graph.finalize", finalize)
    payload = DispatchPayload(job_id=uuid4(), user_id=uuid4(), chat_id=uuid4(), post_format="legacy_html", chat_post_type="single", raw_message="crie um post")
    asyncio.run(build_graph().ainvoke(initial_state(payload)))
    assert legacy_intent.await_count == 1
    assert finalize.await_count == 1
    assert structured.await_count == 0
