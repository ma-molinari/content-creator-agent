"""Enrich profile_text with a vision model summary of optional S3 design references."""

import base64
import logging
import mimetypes
import re
from typing import Any

import boto3
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import PROMPTS_DIR, get_settings
from app.state import AgentState

logger = logging.getLogger(__name__)

_MAX_IMAGES = 8


def _read_prompt() -> str:
    path = PROMPTS_DIR / "describe_references.md"
    return path.read_text(encoding="utf-8")


def _guess_mime(data: bytes, s3_key: str) -> str:
    if len(data) >= 3 and data[0:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(data) >= 8 and data[0:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 6 and (data[0:6] in (b"GIF87a", b"GIF89a")):
        return "image/gif"
    ext = s3_key.rsplit(".", 1)
    if len(ext) == 2:
        mt = mimetypes.guess_type("x." + ext[1].lower())[0]
        if mt and mt.startswith("image/"):
            return mt
    return "image/jpeg"


def _fetch_bytes(key: str) -> bytes:
    settings = get_settings()
    c = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
    )
    o = c.get_object(Bucket=settings.aws_s3_bucket, Key=key)
    return o["Body"].read()


def _strip_wrapped_heading(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(
        r"^#+\s*REFER[ÊE]NCIAS_VISUAIS.*?\n+",
        "",
        t,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return t.strip()


def describe_references(state: AgentState) -> dict[str, Any]:
    keys = (state.get("reference_s3_keys") or [])[:_MAX_IMAGES]
    if not keys:
        return {}
    job_id = state.get("job_id")
    base = (state.get("profile_text") or "").strip()
    system = _read_prompt()
    user_blocks: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "Considere as imagens anexas como referências de estilo. "
                "O contexto de AUDIT/BRAND segue abaixo; o resumo visual deve alinhar-se sem contradizer, "
                "e indicar o que NÃO replicar se aplicável."
                f"\n\n---\n{base}\n---"
            ),
        }
    ]
    for key in keys:
        try:
            raw = _fetch_bytes(key)
        except Exception:
            logger.exception("describe_references: s3 get failed job_id=%s key=%s", job_id, key)
            raise
        mime = _guess_mime(raw, key)
        b64 = base64.standard_b64encode(raw).decode("ascii")
        user_blocks.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{b64}"},
            }
        )
    human = HumanMessage(content=user_blocks)
    settings = get_settings()
    llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.reference_vision_model,
        max_tokens=2000,
    )
    out = llm.invoke(
        [
            SystemMessage(content=system),
            human,
        ]
    )
    text = (getattr(out, "content", None) or str(out) or "").strip()
    if not text:
        logger.warning("describe_references: empty model output job_id=%s", job_id)
        return {}
    if text.lstrip().startswith("##"):
        body = text
    else:
        inner = _strip_wrapped_heading(text)
        body = f"## REFERÊNCIAS_VISUAIS (resumo)\n\n{inner}"
    combined = f"{base}\n\n{body}" if base else body
    return {"profile_text": combined}
