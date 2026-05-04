"""Load prior HTML from S3; refinement when the API signals a follow-up (`expects_slide_refinement`)

or when `existing_slide_html_s3_keys` is populated. Scope for ``edit_slides`` (copy vs layout vs
visual) is inferred heuristically from the user message.
"""

from __future__ import annotations

import asyncio
import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.config import get_settings
from app.nodes.finalize_messages import JOB_FAILURE_REFINEMENT_CONTEXT
from app.state import AgentState, SlideItem, copy_errors

logger = logging.getLogger(__name__)

_MAX_HTML_BYTES = 3_000_000
_COPY_HINTS = (
    "título",
    "titulo",
    "cta",
    "traduz",
    "tradução",
    "traducao",
    "reescrev",
    "texto do",
    "mudar o texto",
    "legenda",
    "typo",
    " errata",
    "palavra ",
    "frase",
    "copy",
    "corrigir texto",
    "corrige o texto",
    "troca o título",
    "troca o titulo",
    "novo título",
    "novo titulo",
    "altera o texto",
    "muda o texto",
    "alterar",
    "atualizar"
)
_LAYOUT_HINTS = (
    "reorganiz",
    "reposicion",
    "nova coluna",
    "layout",
    "mover o",
    "mover a",
    " ordem ",
    "cartão",
    "cartao",
    "blocos",
    "posição",
    "posicao",
    "nova secção",
    "nova secao",
    "outra estrutura",
    "grid diferente",
    "nova linha",
)
_VISUAL_HINTS = (
    " cor ",
    " cores",
    "cor de",
    "coloração",
    "coloracao",
    "tema",
    " rosa",
    " azul",
    " azuis",
    " cinza",
    " cinzas",
    " vermelho",
    " verde",
    " amarelo",
    " branco",
    " preto",
    " roxo",
    " laranja",
    "escuro",
    " claro",
    "dark mode",
    "fundo",
    "background",
    "borda",
    "gradiente",
    "sombra",
    "paleta",
    "accent",
    "#",
    "hex ",
)


def _infer_refinement_scope(message: str) -> str:
    """Infer refinement_scope from simple PT keyword hints in the user message."""
    m = f" {(message or '').lower()} "
    has_copy = any(h in m for h in _COPY_HINTS)
    has_layout = any(h in m for h in _LAYOUT_HINTS)
    has_visual = any(h in m for h in _VISUAL_HINTS)
    if has_copy and (has_layout or has_visual):
        return "mixed"
    if has_copy:
        return "copy"
    if has_layout:
        return "layout"
    if has_visual:
        return "visual_only"
    return "mixed"


def _filename_from_key(key: str) -> str:
    base = (key or "").rsplit("/", 1)[-1].strip()
    return base if base.lower().endswith(".html") else f"{base}.html" if base else "slide.html"


def _get_html_bytes_sync(client, bucket: str, key: str) -> bytes:
    o = client.get_object(Bucket=bucket, Key=key)
    body = o["Body"]
    data = body.read(_MAX_HTML_BYTES + 1)
    if len(data) > _MAX_HTML_BYTES:
        raise ValueError(f"html object too large key={key!r}")
    return data


async def _fetch_html_slides(keys: list[str], settings, job_id: str) -> list[SlideItem]:
    if not keys:
        return []
    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    bucket = settings.aws_s3_bucket

    async def one(k: str) -> SlideItem | None:
        try:
            raw = await asyncio.to_thread(_get_html_bytes_sync, client, bucket, k)
            text = raw.decode("utf-8", errors="replace")
            return SlideItem(filename=_filename_from_key(k), html=text)
        except (ClientError, BotoCoreError, ValueError, UnicodeError) as e:
            logger.error("node=detect_intent job_id=%s fetch_html key=%s err=%s", job_id, k, e)
            return None

    results = await asyncio.gather(*(one(k) for k in keys))
    out = [s for s in results if s is not None]
    if len(out) != len(keys):
        return []
    return out


async def detect_intent(state: AgentState) -> dict[str, object]:
    jid = state.get("job_id") or ""
    logger.info("node=detect_intent job_id=%s", jid)
    expects = bool(state.get("expects_slide_refinement"))
    keys = list(state.get("existing_slide_html_s3_keys") or [])
    settings = get_settings()

    def blocked() -> dict[str, object]:
        return {
            "is_refinement": False,
            "existing_slide_html": [],
            "refinement_context_unavailable": True,
            "errors": copy_errors(state) + [JOB_FAILURE_REFINEMENT_CONTEXT],
        }

    async def build_refinement(html_keys: list[str]) -> dict[str, object] | None:
        slides = await _fetch_html_slides(html_keys, settings, jid)
        if not slides or len(slides) != len(html_keys):
            logger.warning(
                "node=detect_intent job_id=%s refinement aborted (S3 HTML fetch failed or incomplete)",
                jid,
            )
            return None
        raw_message = state.get("raw_message") or ""
        refinement_scope = _infer_refinement_scope(raw_message)
        logger.info(
            "node=detect_intent job_id=%s refinement_scope=%s (from S3 HTML, no intent LLM)",
            jid,
            refinement_scope,
        )
        return {
            "is_refinement": True,
            "existing_slide_html": slides,
            "requested_slide_count": len(slides),
            "refinement_scope": refinement_scope,
        }

    if expects:
        if not keys:
            logger.warning(
                "node=detect_intent job_id=%s expects_slide_refinement but no html s3 keys", jid
            )
            return blocked()
        refined = await build_refinement(keys)
        if refined is None:
            return blocked()
        return refined

    if not keys:
        return {"is_refinement": False, "existing_slide_html": []}

    refined = await build_refinement(keys)
    if refined is None:
        return blocked()
    return refined
