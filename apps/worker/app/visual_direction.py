"""Extract bounded, user-isolated visual directions from authorized references."""

from __future__ import annotations

import asyncio
import base64
from collections import OrderedDict
import hashlib
import json
import logging
from threading import Lock
from time import monotonic
from typing import Literal

import boto3
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import Field, ValidationError, model_validator
from typing_extensions import Self

from app.config import get_settings
from app.llm_messages import langchain_message_text
from app.post_document import Color, _StrictModel
from app.s3_image_utils import fetch_bytes_limited, guess_mime

logger = logging.getLogger(__name__)
_VERSION = "visual-direction-1/prompt-1"
_TTL = 3600
_MAX_CACHE = 128
_MAX_ATTEMPTS = 3
_cache: OrderedDict[str, tuple[float, str]] = OrderedDict()
_cache_lock = Lock()
_SYSTEM = """Analise somente as imagens fornecidas, sem inventar elementos não observados.
Retorne apenas JSON conforme o schema. Use status uncertain para conflitos ou dúvidas,
absent quando a cor não puder ser identificada, e observed apenas para evidência visual.
Não inclua textos das imagens, URLs, HTML nem CSS.
"""


class ColorObservation(_StrictModel):
    status: Literal["observed", "uncertain", "absent"]
    value: Color | None

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (self.status == "observed") != (self.value is not None):
            raise ValueError("color status and value are inconsistent")
        return self


class ObservedPalette(_StrictModel):
    background: ColorObservation
    text: ColorObservation
    accent: ColorObservation


class DecorationObservation(_StrictModel):
    status: Literal["observed", "uncertain"]
    kind: Literal["bar", "line"]
    position: Literal["top", "middle", "bottom"]
    color: Color | None


class VisualDirection(_StrictModel):
    palette: ObservedPalette
    decorations: list[DecorationObservation] = Field(max_length=8)


class VisualDirectionError(Exception):
    """A complete, valid reference analysis could not be produced."""


class _ReapplyDecision(_StrictModel):
    decision: Literal["yes", "no", "uncertain"]


async def requests_reference_reapplication(request: str) -> bool:
    settings = get_settings()
    llm = ChatOpenAI(api_key=settings.openai_api_key, model=settings.openai_chat_model,
                     max_tokens=100, temperature=0)
    system = ("Determine se a edição pede explicitamente reaplicar as referências visuais atuais. "
              "Retorne somente JSON com decision: yes, no ou uncertain. "
              "Pedido de não usar referências é no; em dúvida retorne uncertain.")
    for _ in range(_MAX_ATTEMPTS):
        try:
            response = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=request)])
            decision = _ReapplyDecision.model_validate_json(langchain_message_text(response)).decision
            if decision == "uncertain":
                raise VisualDirectionError("Não foi possível identificar se deseja reaplicar as referências. Reformule o pedido.")
            return decision == "yes"
        except (ValidationError, ValueError):
            continue
    raise VisualDirectionError("Não foi possível identificar se deseja reaplicar as referências. Reformule o pedido.")


def _key(user_id: str, model: str, images: list[bytes]) -> str:
    digest = hashlib.sha256()
    for value in [user_id.encode(), model.encode(), _VERSION.encode(), *images]:
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)
    return digest.hexdigest()


async def extract_visual_direction(*, user_id: str, reference_keys: list[str], reapply: bool = False) -> VisualDirection | None:
    started = monotonic()
    if not user_id:
        raise VisualDirectionError("Não foi possível identificar o usuário para analisar as referências.")
    if not reference_keys:
        if reapply:
            raise VisualDirectionError("Adicione referências visuais antes de reaplicá-las.")
        return None
    if len(reference_keys) > 8:
        raise VisualDirectionError("Use no máximo oito referências visuais por vez.")
    settings = get_settings()
    client = boto3.client("s3", region_name=settings.aws_region, aws_access_key_id=settings.aws_access_key_id,
                          aws_secret_access_key=settings.aws_secret_access_key)
    fetched = await asyncio.gather(*[asyncio.to_thread(fetch_bytes_limited, client, settings.aws_s3_bucket, key,
                                                       settings.reference_image_max_bytes) for key in reference_keys],
                                   return_exceptions=True)
    if any(isinstance(item, BaseException) for item in fetched):
        logger.info("event=visual_direction outcome=failed reason=fetch duration_ms=%d", int((monotonic() - started) * 1000))
        raise VisualDirectionError("Não foi possível carregar todas as referências visuais. Tente novamente.")
    images: list[bytes] = list(fetched)  # type: ignore[assignment]
    cache_key = _key(user_id, settings.reference_vision_model, images)
    now = monotonic()
    with _cache_lock:
        for key, (expires, _) in list(_cache.items()):
            if expires <= now:
                del _cache[key]
        cached = _cache.get(cache_key)
        if cached and cached[0] > now:
            _cache.move_to_end(cache_key)
            logger.info("event=visual_direction outcome=success cache=hit duration_ms=%d", int((now - started) * 1000))
            return VisualDirection.model_validate_json(cached[1])
    blocks: list[dict] = [{"type": "text", "text": json.dumps(VisualDirection.model_json_schema(), ensure_ascii=False)}]
    for key, raw in zip(reference_keys, images):
        mime = guess_mime(raw, key)
        blocks.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"}})
    llm = ChatOpenAI(api_key=settings.openai_api_key, model=settings.reference_vision_model, max_tokens=2000)
    for _ in range(_MAX_ATTEMPTS):
        try:
            response = await llm.ainvoke([SystemMessage(content=_SYSTEM), HumanMessage(content=blocks)])
            direction = VisualDirection.model_validate_json(langchain_message_text(response))
        except (ValidationError, ValueError):
            continue
        except Exception:
            logger.info("event=visual_direction outcome=failed reason=model duration_ms=%d", int((monotonic() - started) * 1000))
            raise VisualDirectionError("Não foi possível analisar as referências visuais. Tente novamente.") from None
        with _cache_lock:
            _cache[cache_key] = (monotonic() + _TTL, direction.model_dump_json())
            _cache.move_to_end(cache_key)
            while len(_cache) > _MAX_CACHE:
                _cache.popitem(last=False)
        logger.info("event=visual_direction outcome=success cache=miss duration_ms=%d decorations=%d", int((monotonic() - started) * 1000), len(direction.decorations))
        return direction
    logger.info("event=visual_direction outcome=failed reason=schema duration_ms=%d", int((monotonic() - started) * 1000))
    raise VisualDirectionError("Não foi possível analisar as referências visuais. Tente novamente.")
