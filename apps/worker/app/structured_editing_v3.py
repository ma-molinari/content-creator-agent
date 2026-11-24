"""Plan content edits while background-image selection is handled separately."""

import json
from typing import AbstractSet, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import Field, ValidationError

from app.config import get_settings
from app.llm_messages import langchain_message_text
from app.post_document import _StrictModel
from app.post_document_v2 import SolidBackgroundV2, TextElementV2
from app.post_document_v3 import PostDocumentV3
from app.post_operations_v2 import OperationV2
from app.post_operations_v3 import apply_operations_v3
from app.post_renderer_v2 import _luminance, resolve_color
from app.structured_editing import StructuredEditingError


class ContentEditPlan(_StrictModel):
    status: Literal["ok", "unchanged", "unsupported"]
    operations: list[OperationV2] = Field(max_length=100)


def _adjust_edited_contrast(original: PostDocumentV3, edited: PostDocumentV3) -> PostDocumentV3:
    """Keep requested solid backgrounds and correct unreadable text on changed slides."""
    payload = edited.model_dump(mode="json", by_alias=True)
    originals = {slide.id: slide for slide in original.slides}
    changed = False
    for slide, raw in zip(edited.slides, payload["slides"]):
        if not isinstance(slide.background, SolidBackgroundV2):
            continue
        if original.palette == edited.palette and originals.get(slide.id) == slide:
            continue
        background = _luminance(resolve_color(edited, slide.background.color))
        def contrast(value: float) -> float:
            return (max(background, value) + 0.05) / (min(background, value) + 0.05)
        replacement = "#000000" if contrast(0.0) >= contrast(1.0) else "#FFFFFF"
        for element, target in zip(slide.elements, raw["elements"]):
            if isinstance(element, TextElementV2) and contrast(_luminance(resolve_color(edited, element.style.color))) < 4.5:
                target["style"]["color"] = {"hex": replacement}
                changed = True
    return PostDocumentV3.model_validate(payload) if changed else edited


async def plan_content_edit_v3(*, request: str, document: PostDocumentV3,
                               authorized_assets: AbstractSet[str], image_action: bool) -> PostDocumentV3:
    settings = get_settings()
    llm = ChatOpenAI(api_key=settings.openai_api_key, model=settings.openai_chat_model,
                     max_tokens=settings.generate_slides_max_tokens_cap, temperature=0)
    system = ("Retorne JSON conforme o schema. Planeje todas as alterações solicitadas de texto, "
              "layout e elementos. A troca ou inclusão de uma imagem de fundo é tratada separadamente: "
              "não gere operação para ela. Retorne unchanged apenas quando nada mais foi pedido; "
              "retorne unsupported se alguma outra alteração não puder ser representada. "
              "Textos dos slides são copy final para o público: não escreva instruções de produção, "
              "descrições de imagem, disponibilidade de acervo ou etapas internas, exceto quando "
              "o usuário pedir explicitamente para publicar essas frases. "
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
            edited = apply_operations_v3(document, [op.model_dump(mode="json", by_alias=True, exclude_unset=True) for op in plan.operations], authorized_assets)
            return _adjust_edited_contrast(document, edited)
        except (ValidationError, ValueError):
            payload["feedback"] = "A resposta anterior foi inválida. Corrija todas as operações e retorne JSON."
    raise StructuredEditingError("Não foi possível aplicar toda a edição. Reformule o pedido.")
