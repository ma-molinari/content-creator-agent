"""Vision summaries for user-supplied attachment images."""

from __future__ import annotations

import asyncio
import base64
import logging
import re
from typing import Any, cast

import boto3
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings, read_prompt_md
from app.llm_messages import langchain_message_text
from app.s3_image_utils import fetch_bytes_limited, guess_mime, presign_get_url
from app.state import AgentState, copy_errors

logger = logging.getLogger(__name__)

_INTENT_RE = re.compile(
    r"\b(use|usa|coloque|ponha|adicion[ea]|inclu[ai]|"
    r"no\s+slide\s+\d+|como\s+(capa|fundo|hero|background)|"
    r"na\s+capa|primeir[oa]\s+slide|substitu[ia]r?)\b",
    re.IGNORECASE,
)

_DESCRIPTION_RE = re.compile(
    r"^\s*(\d+)\.\s*(.+?)(?=\n\s*\d+\.|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _parse_numbered_descriptions(text: str, n: int) -> list[str]:
    out = [""] * n
    for m in _DESCRIPTION_RE.finditer(text.strip()):
        idx = int(m.group(1))
        body = (m.group(2) or "").strip()
        if 1 <= idx <= n:
            out[idx - 1] = body
    return out


async def describe_user_attachments(state: AgentState) -> dict[str, object]:
    keys = state.get("user_attachment_s3_keys") or []
    if not keys:
        return {}

    raw_msg = cast(str | None, state.get("raw_message"))
    intent = "explicit" if _INTENT_RE.search(raw_msg or "") else "cover_default"

    settings = get_settings()
    job_id = state.get("job_id")
    system = read_prompt_md("describe_user_attachments.md")
    errors = copy_errors(state)

    bucket = settings.aws_s3_bucket
    max_bytes = settings.reference_image_max_bytes
    n = len(keys)

    s3_client: Any = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )

    signed_urls: list[str] = []
    for key in keys:
        try:
            signed_urls.append(presign_get_url(s3_client, bucket, key))
        except Exception:
            logger.exception(
                "describe_user_attachments: presign failed job_id=%s key=%s",
                job_id,
                key,
            )
            signed_urls.append("")

    fetch_out = await asyncio.gather(
        *[
            asyncio.to_thread(fetch_bytes_limited, s3_client, bucket, key, max_bytes)
            for key in keys
        ],
        return_exceptions=True,
    )

    blobs: list[bytes] = []
    mime_types: list[str] = ["image/jpeg"] * n
    fetch_any_error = False

    for idx, (key, result) in enumerate(zip(keys, fetch_out, strict=True)):
        if isinstance(result, BaseException):
            fetch_any_error = True
            if isinstance(result, ValueError):
                logger.warning(
                    "describe_user_attachments: attachment exceeds max_bytes job_id=%s key=%s",
                    job_id,
                    key,
                )
                errors.append(
                    f"describe_user_attachments: imagem grande demais ({max_bytes} bytes) — {key}"
                )
            else:
                logger.exception(
                    "describe_user_attachments: s3 fetch failed job_id=%s key=%s",
                    job_id,
                    key,
                )
                errors.append(f"describe_user_attachments: falha S3 {key}: {result!s}")
            continue
        blob = cast(bytes, result)
        blobs.append(blob)
        mime_types[idx] = guess_mime(blob, key)

    degraded: dict[str, object] = {
        "user_attachment_descriptions": [""] * n,
        "user_attachment_signed_urls": signed_urls,
        "user_attachment_intent": intent,
        "user_attachment_mime_types": mime_types,
    }

    if fetch_any_error or len(blobs) != n:
        if errors:
            degraded["errors"] = errors
        return degraded

    user_blocks: list[dict[str, object]] = [
        {
            "type": "text",
            "text": (
                f"Há exatamente {n} imagens, na ordem 1 até {n}. "
                "Descreva cada uma segundo as regras do sistema "
                "(lista numerada 1…N)."
            ),
        }
    ]

    for key, blob in zip(keys, blobs, strict=True):
        mime = guess_mime(blob, key)
        b64 = base64.standard_b64encode(blob).decode("ascii")
        user_blocks.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            }
        )

    descriptions = [""] * n
    llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.reference_vision_model,
        max_tokens=3500,
    )
    human = HumanMessage(content=user_blocks)
    try:
        model_out = await llm.ainvoke([SystemMessage(content=system), human])
        descriptions = _parse_numbered_descriptions(langchain_message_text(model_out) or "", n)
    except Exception as exc:
        logger.exception(
            "describe_user_attachments: llm invoke failed job_id=%s key_count=%s",
            job_id,
            len(keys),
        )
        errors.append(f"describe_user_attachments: falha modelo de visão: {exc!s}")

    merged: dict[str, object] = {
        "user_attachment_descriptions": descriptions,
        "user_attachment_signed_urls": signed_urls,
        "user_attachment_intent": intent,
        "user_attachment_mime_types": mime_types,
    }
    if errors:
        merged["errors"] = errors

    return merged
