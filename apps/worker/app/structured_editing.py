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
) -> PostDocumentV1:
    settings = get_settings()
    llm = ChatOpenAI(api_key=settings.openai_api_key, model=settings.openai_chat_model,
                     max_tokens=settings.generate_slides_max_tokens_cap, temperature=0)
    payload = {
        "request": request,
        "document": document.model_dump(mode="json", by_alias=True),
        "authorizedAssetIds": sorted(authorized_assets),
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
