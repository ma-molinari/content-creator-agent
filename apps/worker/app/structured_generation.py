"""Generate a structured post document with bounded retries."""

from __future__ import annotations

import json
from typing import AbstractSet, Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.config import get_settings
from app.llm_messages import langchain_message_text
from app.post_document import ImageElement, PostDocumentV1

_SYSTEM = """Crie um documento JSON para um post do Instagram seguindo o schema fornecido.
Use somente os IDs de imagem autorizados. Não produza HTML, CSS ou URLs.
Responda apenas com JSON válido, sem markdown."""
_MAX_ATTEMPTS = 3


class StructuredGenerationError(Exception):
    """No valid document was produced within the retry budget."""


async def generate_structured_post(
    *, request: str, profile_text: str, post_type: str, authorized_assets: AbstractSet[str],
    requested_slide_count: int | None = None,
) -> PostDocumentV1:
    settings = get_settings()
    llm = ChatOpenAI(api_key=settings.openai_api_key, model=settings.openai_chat_model,
                     max_tokens=settings.generate_slides_max_tokens_cap)
    payload: dict[str, Any] = {
        "request": request,
        "profile": profile_text,
        "postType": post_type,
        "requestedSlideCount": requested_slide_count,
        "authorizedAssetIds": sorted(authorized_assets),
        "schema": PostDocumentV1.model_json_schema(by_alias=True),
    }
    for attempt in range(_MAX_ATTEMPTS):
        response = await llm.ainvoke([
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ])
        try:
            document = PostDocumentV1.model_validate_json(langchain_message_text(response))
            if document.post_type != post_type:
                raise ValueError("post type does not match request")
            if requested_slide_count is not None and len(document.slides) != requested_slide_count:
                raise ValueError("slide count does not match request")
            if any(isinstance(item, ImageElement) and item.asset_id not in authorized_assets
                   for slide in document.slides for item in slide.elements):
                raise ValueError("unauthorized image asset")
            return document
        except (ValidationError, ValueError):
            # Do not send validation details that could include user content back to logs or clients.
            if attempt + 1 < _MAX_ATTEMPTS:
                payload["retryFeedback"] = "A saída anterior não respeitou o schema ou os requisitos. Corrija e retorne somente JSON válido."
    raise StructuredGenerationError("Não foi possível gerar um post estruturado válido.")
