"""Validate mandatory user attachment usage in generated HTML."""

from __future__ import annotations

import logging
import re
from html import unescape
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from app.state import AgentState, copy_errors

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_CSS_URL_RE = re.compile(r"""url\(\s*(['"]?)([^'")\s]+)\1\s*\)""", re.I)
_PLACEHOLDER_RE = re.compile(
    r"\b(?:imagem\s+em\s+anexo|imagem\s+anexada|foto\s+em\s+anexo|visual\s+aqui|placeholder)\b",
    re.I,
)


def _url_path_contains_key(url: str, s3_key: str) -> bool:
    if not url or not s3_key:
        return False
    try:
        path = unquote(urlparse(url).path or "")
    except ValueError:
        return False
    normalized_path = path.lstrip("/")
    normalized_key = s3_key.lstrip("/")
    return normalized_path == normalized_key or normalized_path.endswith("/" + normalized_key)


def _same_attachment(candidate: str, url: str, s3_key: str) -> bool:
    value = unquote(unescape(candidate or "")).strip()
    if not value:
        return False
    if url and (value == url or value in url or url in value):
        return True
    key = (s3_key or "").strip()
    if key and key in value:
        return True
    return _url_path_contains_key(value, key)


def _style_references_attachment(style: str, url: str, s3_key: str) -> bool:
    if not style:
        return False
    return any(_same_attachment(m.group(2), url, s3_key) for m in _CSS_URL_RE.finditer(style))


def _attachment_referenced_as_visual(html: str, url: str, s3_key: str) -> bool:
    soup = BeautifulSoup(html or "", "html.parser")

    for tag_name, attr in (
        ("img", "src"),
        ("source", "src"),
        ("video", "poster"),
    ):
        for node in soup.find_all(tag_name):
            val = node.get(attr)
            if isinstance(val, str) and _same_attachment(val, url, s3_key):
                return True

    for node in soup.find_all(True):
        srcset = node.get("srcset")
        if isinstance(srcset, str):
            for piece in srcset.split(","):
                candidate = piece.strip().split()[0] if piece.strip() else ""
                if _same_attachment(candidate, url, s3_key):
                    return True
        style = node.get("style")
        if isinstance(style, str) and _style_references_attachment(style, url, s3_key):
            return True

    for style_tag in soup.find_all("style"):
        css = style_tag.get_text("\n")
        if _style_references_attachment(css, url, s3_key):
            return True

    return False


def _has_attachment_placeholder(html: str) -> bool:
    text = BeautifulSoup(html or "", "html.parser").get_text(" ")
    return bool(_PLACEHOLDER_RE.search(text))


def _use_instruction(item_id: object) -> str:
    return (
        f"use a URL presignada de attachment_requirements id={item_id} "
        "literalmente em <img src> ou background-image."
    )


def validate_attachment_usage(state: AgentState) -> dict[str, object]:
    logger.info("node=validate_attachment_usage job_id=%s", state.get("job_id"))
    plan = list(state.get("attachment_plan") or [])
    if not plan:
        return {}
    slides = list(state.get("slides_html") or [])
    diagnostics: list[str] = []
    for item in plan:
        url = str(item.get("url") or "")
        s3_key = str(item.get("s3_key") or "")
        required = item.get("required_slide_number")
        if not url:
            diagnostics.append(f"attachment_usage: anexo {item.get('id')} sem URL presignada.")
            continue
        if isinstance(required, int) and required > 0:
            candidates = [
                s for s in slides
                if f"{required:02d}" in (s.get("filename") or "") or str(required) in (s.get("filename") or "")
            ]
            if not candidates:
                candidates = slides[required - 1:required] if len(slides) >= required else []
            if any(_has_attachment_placeholder(s.get("html") or "") for s in candidates):
                diagnostics.append(
                    f"attachment_usage: slide {required} usa placeholder textual para o anexo; "
                    f"{_use_instruction(item.get('id'))}"
                )
            elif not any(_attachment_referenced_as_visual(s.get("html") or "", url, s3_key) for s in candidates):
                diagnostics.append(
                    f"attachment_usage: anexo {item.get('id')} obrigatório no slide {required} não foi usado; "
                    f"{_use_instruction(item.get('id'))}"
                )
        elif not any(_attachment_referenced_as_visual(s.get("html") or "", url, s3_key) for s in slides):
            diagnostics.append(
                f"attachment_usage: anexo {item.get('id')} não foi usado em nenhum slide; "
                f"{_use_instruction(item.get('id'))}"
            )

    if not diagnostics:
        return {}
    retry = int(state.get("retry_count") or 0)
    out: dict[str, object] = {
        "slides_html": [],
        "errors": copy_errors(state) + diagnostics,
        "validation_report": {
            "category": "attachment_usage",
            "actionable_messages": diagnostics,
            "retry_count": retry,
        },
    }
    if retry < _MAX_RETRIES:
        out["retry_count"] = retry + 1
    return out


def route_after_attachment_usage(state: AgentState) -> str:
    if state.get("slides_html"):
        return "continue"
    return "retry" if int(state.get("retry_count") or 0) < _MAX_RETRIES else "fail"
