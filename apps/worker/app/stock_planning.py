"""Convert a user request into a bounded image search query."""

import json
import re
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import Field, ValidationError, model_validator
from typing_extensions import Self

from app.config import get_settings
from app.llm_messages import langchain_message_text
from app.post_document import _StrictModel
from app.structured_editing import StructuredEditingError


class StockPlan(_StrictModel):
    action: Literal["none", "replace", "unsupported"]
    query: str | None = Field(max_length=120)
    slide_number: int | None = Field(ge=1, le=20)

    @model_validator(mode="after")
    def validate_action(self) -> Self:
        if self.action == "replace" and (not self.query or not self.query.strip() or self.slide_number is None):
            raise ValueError("search and slide are required")
        if self.action in ("none", "unsupported") and (self.query is not None or self.slide_number is not None):
            raise ValueError("no image action must not include search or slide")
        return self


async def plan_stock_action(*, request: str, mode: Literal["create", "edit"], slide_count: int) -> StockPlan:
    if mode == "edit" and not re.search(r"\b(?:imagem|imagens|foto|fotos|fotografia|fotografias|fundo)\b", request, re.IGNORECASE):
        return StockPlan(action="none", query=None, slide_number=None)
    settings = get_settings()
    llm = ChatOpenAI(api_key=settings.openai_api_key, model=settings.openai_chat_model, temperature=0,
                     max_tokens=500)
    system = ("Retorne somente JSON conforme o schema. Na criação, escolha replace e o primeiro slide, "
              "exceto quando o usuário pedir sem imagens. Na edição, escolha replace somente se o usuário "
              "pedir adicionar ou trocar uma imagem de fundo; caso contrário escolha none. Use slide 1 "
              "quando não especificado. Se o pedido exigir imagens em mais de um slide, escolha unsupported; "
              "nunca ignore parte do pedido. A busca deve conter apenas palavras genéricas para encontrar uma "
              "fotografia; nunca inclua nomes próprios, dados pessoais ou trechos privados do pedido.")
    payload = {"request": request, "mode": mode, "slideCount": slide_count, "schema": StockPlan.model_json_schema()}
    for _ in range(3):
        response = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=json.dumps(payload, ensure_ascii=False))])
        try:
            plan = StockPlan.model_validate_json(langchain_message_text(response))
            if plan.slide_number is not None and plan.slide_number > slide_count:
                raise ValueError("slide outside post")
            if plan.action == "unsupported":
                raise StructuredEditingError("Por enquanto, solicite uma imagem por vez.")
            return plan
        except (ValidationError, ValueError):
            payload["feedback"] = "A resposta não respeitou o schema ou o número de slides. Corrija o JSON."
    raise ValueError("Não foi possível identificar a imagem solicitada. Reformule o pedido.")
