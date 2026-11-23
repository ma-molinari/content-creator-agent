"""Plan structured edits without changing the original document."""

from __future__ import annotations

import json
from typing import AbstractSet, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import Field, ValidationError

from app.config import get_settings
from app.llm_messages import langchain_message_text
from app.post_document import PostDocumentV1, _StrictModel
from app.post_operations import Operation, apply_operations
from app.post_document_v2 import PostDocumentV2
from app.post_operations_v2 import OperationV2, apply_operations_v2
from app.visual_direction import VisualDirection

_SYSTEM = """Interprete o pedido de edição e retorne somente JSON válido conforme o schema.
Emita apenas operações necessárias ao pedido. Se ele for ambíguo ou não puder ser
representado pelas operações disponíveis, retorne status=unsupported e uma lista vazia.
Não use HTML, CSS ou URLs. Nunca altere a quantidade ou a ordem dos slides."""
_MAX_ATTEMPTS = 3


class EditPlan(_StrictModel):
    status: Literal["ok", "unsupported"]
    operations: list[Operation] = Field(max_length=100)


class StructuredEditingError(Exception):
    """The edit could not be applied safely."""


async def plan_structured_edit(
    *, request: str, document: PostDocumentV1, authorized_assets: AbstractSet[str],
    asset_requirements: list[dict[str, object]] | None = None,
) -> PostDocumentV1:
    settings = get_settings()
    llm = ChatOpenAI(api_key=settings.openai_api_key, model=settings.openai_chat_model,
                     max_tokens=settings.generate_slides_max_tokens_cap, temperature=0)
    payload = {
        "request": request,
        "document": document.model_dump(mode="json", by_alias=True),
        "authorizedAssetIds": sorted(authorized_assets),
        "assetRequirements": asset_requirements or [],
        "schema": EditPlan.model_json_schema(by_alias=True),
    }
    for attempt in range(_MAX_ATTEMPTS):
        response = await llm.ainvoke([
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ])
        try:
            plan = EditPlan.model_validate_json(langchain_message_text(response))
            if plan.status == "unsupported":
                if plan.operations:
                    raise ValueError("unsupported edit contains operations")
                raise StructuredEditingError("Não foi possível aplicar a edição. Reformule o pedido.")
            if not plan.operations:
                raise ValueError("edit plan is empty")
            operations = [operation.model_dump(mode="json", by_alias=True) for operation in plan.operations]
            return apply_operations(document, operations, authorized_assets)
        except (ValidationError, ValueError):
            if attempt + 1 < _MAX_ATTEMPTS:
                payload["retryFeedback"] = "A saída anterior não respeitou o schema ou contém operações inválidas. Corrija e retorne apenas JSON válido."
    raise StructuredEditingError("Não foi possível aplicar a edição. Reformule o pedido.")


class EditPlanV2(_StrictModel):
    status: Literal["ok", "unsupported"]
    operations: list[OperationV2] = Field(max_length=100)


async def plan_structured_edit_v2(
    *, request: str, document: PostDocumentV2, authorized_assets: AbstractSet[str],
    reapply_references: bool = False, visual_direction: VisualDirection | None = None,
    asset_requirements: list[dict[str, object]] | None = None,
) -> PostDocumentV2:
    if reapply_references != (visual_direction is not None):
        raise StructuredEditingError("Não foi possível aplicar as referências. Reformule o pedido.")
    settings = get_settings()
    llm = ChatOpenAI(api_key=settings.openai_api_key, model=settings.openai_chat_model,
                     max_tokens=settings.generate_slides_max_tokens_cap, temperature=0)
    payload = {"request": request, "document": document.model_dump(mode="json", by_alias=True),
               "authorizedAssetIds": sorted(authorized_assets), "assetRequirements": asset_requirements or [],
               "schema": EditPlanV2.model_json_schema(by_alias=True)}
    if visual_direction:
        payload["visualDirection"] = visual_direction.model_dump(mode="json")
    system = _SYSTEM + "\nAltere tokens compartilhados somente quando o pedido autorizar todos os efeitos. Preserve campos não solicitados. Em set_text_style forneça o estilo completo anterior com apenas as alterações solicitadas."
    for attempt in range(_MAX_ATTEMPTS):
        response = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=json.dumps(payload, ensure_ascii=False))])
        try:
            plan = EditPlanV2.model_validate_json(langchain_message_text(response))
            if plan.status == "unsupported":
                if plan.operations:
                    raise ValueError("unsupported edit contains operations")
                raise StructuredEditingError("Não foi possível aplicar a edição. Reformule o pedido.")
            if not plan.operations:
                raise ValueError("edit plan is empty")
            operations = [operation.model_dump(mode="json", by_alias=True, exclude_unset=True) for operation in plan.operations]
            return apply_operations_v2(document, operations, authorized_assets)
        except (ValidationError, ValueError):
            if attempt + 1 < _MAX_ATTEMPTS:
                payload["retryFeedback"] = "A saída anterior não respeitou o schema ou contém operações inválidas. Corrija e retorne apenas JSON válido."
    raise StructuredEditingError("Não foi possível aplicar a edição. Reformule o pedido.")
