"""Classify edit vs new generation; load prior HTML from S3 when refining."""

from __future__ import annotations

import asyncio
import json
import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings, read_prompt_md
from app.llm_messages import langchain_message_text
from app.state import AgentState, SlideItem

logger = logging.getLogger(__name__)

_MAX_HTML_BYTES = 3_000_000


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
    keys = list(state.get("existing_slide_html_s3_keys") or [])
    if not keys:
        return {"is_refinement": False, "existing_slide_html": []}

    settings = get_settings()
    system = read_prompt_md("detect_intent.md")
    llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_chat_model,
        temperature=0,
        max_tokens=50,
    )
    msg = await llm.ainvoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=state.get("raw_message") or ""),
        ]
    )
    try:
        parsed = json.loads(langchain_message_text(msg).strip())
        intent = str(parsed.get("intent", "edit")).strip().lower()
    except (json.JSONDecodeError, TypeError, ValueError):
        intent = "edit"

    if intent != "edit":
        return {"is_refinement": False, "existing_slide_html": []}

    slides = await _fetch_html_slides(keys, settings, jid)
    if not slides:
        logger.warning(
            "node=detect_intent job_id=%s refinement aborted (html fetch failed or incomplete)",
            jid,
        )
        return {"is_refinement": False, "existing_slide_html": []}

    return {
        "is_refinement": True,
        "existing_slide_html": slides,
        "requested_slide_count": len(slides),
    }
