"""Plan content edits while background-image selection is handled separately."""

import json
from typing import AbstractSet, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import Field, ValidationError

from app.config import get_settings
from app.llm_messages import langchain_message_text
from app.post_document import _StrictModel
from app.post_document_v3 import PostDocumentV3
from app.post_operations_v2 import OperationV2
from app.post_operations_v3 import apply_operations_v3
from app.structured_editing import StructuredEditingError


class ContentEditPlan(_StrictModel):
    status: Literal["ok", "unchanged", "unsupported"]
    operations: list[OperationV2] = Field(max_length=100)


async def plan_content_edit_v3(*, request: str, document: PostDocumentV3,
                               authorized_assets: AbstractSet[str], image_action: bool) -> PostDocumentV3:
    settings = get_settings()
    llm = ChatOpenAI(api_key=settings.openai_api_key, model=settings.openai_chat_model,
                     max_tokens=settings.generate_slides_max_tokens_cap, temperature=0)
    system = ("Retorne JSON conforme o schema. Planeje todas as alterações solicitadas de texto, "
              "layout e elementos. A troca ou inclusão de uma imagem de fundo é tratada separadamente: "
              "não gere operação para ela. Retorne unchanged apenas quando nada mais foi pedido; "
              "retorne unsupported se alguma outra alteração não puder ser representada. "
              "Não use HTML, CSS ou URLs. Não altere o número nem a ordem dos slides.")
    payload = {"request": request, "document": document.model_dump(mode="json", by_alias=True),
               "imageAction": image_action, "authorizedAssetIds": sorted(authorized_assets),
               "schema": ContentEditPlan.model_json_schema(by_alias=True)}
    for _ in range(3):
        response = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=json.dumps(payload, ensure_ascii=False))])
        try:
            plan = ContentEditPlan.model_validate_json(langchain_message_text(response))
            if plan.status == "unsupported":
                if plan.operations: raise ValueError("unsupported plan contains operations")
                raise StructuredEditingError("Não foi possível aplicar toda a edição. Reformule o pedido.")
            if plan.status == "unchanged":
                if plan.operations or not image_action: raise ValueError("empty edit")
                return document
            if not plan.operations: raise ValueError("empty edit")
            return apply_operations_v3(document, [op.model_dump(mode="json", by_alias=True, exclude_unset=True) for op in plan.operations], authorized_assets)
        except (ValidationError, ValueError):
            payload["feedback"] = "A resposta anterior foi inválida. Corrija todas as operações e retorne JSON."
    raise StructuredEditingError("Não foi possível aplicar toda a edição. Reformule o pedido.")
