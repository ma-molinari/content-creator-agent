"""Generate a structured post document with bounded retries."""

from __future__ import annotations

import json
import logging
from typing import AbstractSet, Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import ValidationError

from app.config import get_settings
from app.llm_messages import langchain_message_text
from app.post_document import ImageElement, PostDocumentV1
from app.post_document_v2 import PostDocumentV2, validate_authorized_assets
from app.post_renderer_v2 import validate_post_contrast
from app.visual_direction import VisualDirection

_SYSTEM = """Crie um documento JSON para um post do Instagram seguindo o schema fornecido.
Use somente os IDs de imagem autorizados. Não produza HTML, CSS ou URLs.
Os campos de texto dos slides são conteúdo final destinado ao público. Transforme o tema
em copy publicável; não inclua instruções de produção, descrições de layout ou fotografia,
observações sobre disponibilidade de imagem, acervo, ferramentas ou etapas internas.
Pedidos sobre imagem, fundo e composição orientam a execução, não são frases para o post.
Preserve essas frases apenas quando o usuário solicitar explicitamente que sejam publicadas.
Responda apenas com JSON válido, sem markdown."""
_MAX_ATTEMPTS = 3
logger = logging.getLogger(__name__)


class StructuredGenerationError(Exception):
    """No valid document was produced within the retry budget."""


async def generate_structured_post(
    *, request: str, profile_text: str, post_type: str, authorized_assets: AbstractSet[str],
    requested_slide_count: int | None = None, asset_requirements: list[dict[str, object]] | None = None,
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
        "assetRequirements": asset_requirements or [],
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


async def generate_structured_post_v2(
    *, request: str, profile_text: str, post_type: str, authorized_assets: AbstractSet[str],
    visual_direction: VisualDirection | None = None, requested_slide_count: int | None = None,
    asset_requirements: list[dict[str, object]] | None = None,
) -> PostDocumentV2:
    settings = get_settings()
    llm = ChatOpenAI(api_key=settings.openai_api_key, model=settings.openai_chat_model,
                     max_tokens=settings.generate_slides_max_tokens_cap)
    payload: dict[str, Any] = {
        "request": request, "profile": profile_text, "postType": post_type,
        "requestedSlideCount": requested_slide_count, "authorizedAssetIds": sorted(authorized_assets),
        "assetRequirements": asset_requirements or [], "schema": PostDocumentV2.model_json_schema(by_alias=True),
        "visualDirection": visual_direction.model_dump(mode="json") if visual_direction else None,
    }
    system = _SYSTEM + """
A direção visual é orientação aproximada. Não trate detalhes incertos como observados.
Em cada decoração do tipo line, corner deve ser square; rounded é permitido somente em bar.
Use no máximo quatro decorações e doze elementos por slide. As cores do texto e do fundo
devem manter contraste mínimo de 4,5:1; prefira combinações de alta legibilidade.
Os layouts hero e editorial iniciam o fluxo na parte superior; quote centraliza o fluxo
verticalmente. Para um destaque observado no topo, prefira hero ou editorial e coloque
a decoração no início dos elementos, sem prometer reprodução exata.
"""
    for attempt in range(_MAX_ATTEMPTS):
        response = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=json.dumps(payload, ensure_ascii=False))])
        try:
            document = PostDocumentV2.model_validate_json(langchain_message_text(response))
            if document.post_type != post_type or (requested_slide_count is not None and len(document.slides) != requested_slide_count):
                raise ValueError("post type or slide count does not match request")
            validate_authorized_assets(document, authorized_assets)
            validate_post_contrast(document)
            return document
        except (ValidationError, ValueError) as exc:
            if str(exc) == "text contrast is insufficient":
                logger.info("[metrics] event=structured_validation schema=2 outcome=failed reason=contrast")
            if attempt + 1 < _MAX_ATTEMPTS:
                payload["retryFeedback"] = (
                    "A saída anterior não respeitou o contrato ou o contraste mínimo de 4,5:1. "
                    "Corrija ambos, use corner square em toda linha e retorne somente JSON válido."
                )
    raise StructuredGenerationError("Não foi possível gerar um post estruturado válido.")
