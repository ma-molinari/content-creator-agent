"""Structured new-vs-edit intent detection."""

from __future__ import annotations

import logging
import re

from app.state import AgentState

logger = logging.getLogger(__name__)

_NEW_HINT = re.compile(
    r"\b(novo|nova|outro assunto|come[cç]a do zero|do zero|cria(?:r)? um|faz(?:er)? um|"
    r"post sobre|carrossel sobre|new|from scratch|another topic)\b",
    re.IGNORECASE,
)
_EDIT_HINT = re.compile(
    r"\b(edit|editar|edite|ajust|alter|mud|troca|substitu|refa[çc]|refin|melhor|"
    r"mant[eé]m|manter|preserv|sem mudar|only change|keep|replace|change|adjust|improve)\b",
    re.IGNORECASE,
)
_COPY_HINT = re.compile(r"\b(t[ií]tulo|cta|texto|copy|legenda|traduz|reescrev|corrig|palavra|frase)\b", re.I)
_LAYOUT_HINT = re.compile(r"\b(layout|reposicion|mover|coluna|ordem|grid|estrutura|blocos?)\b", re.I)
_VISUAL_HINT = re.compile(r"\b(cor|cores|tema|fundo|background|escuro|claro|borda|gradiente|sombra|paleta|contraste)\b", re.I)


def _scope(message: str) -> str:
    has_copy = bool(_COPY_HINT.search(message))
    has_layout = bool(_LAYOUT_HINT.search(message))
    has_visual = bool(_VISUAL_HINT.search(message))
    if has_copy and (has_layout or has_visual):
        return "mixed"
    if has_copy:
        return "copy"
    if has_layout:
        return "layout"
    if has_visual:
        return "visual_only"
    return "mixed"


def intent_detect(state: AgentState) -> dict[str, object]:
    jid = state.get("job_id")
    logger.info("node=intent_detect job_id=%s", jid)
    msg = state.get("raw_message") or ""
    sources = list(state.get("existing_slide_sources") or [])
    if not sources:
        sources = [
            {"slide_number": i + 1, "html_s3_key": key}
            for i, key in enumerate(state.get("existing_slide_html_s3_keys") or [])
        ]
    has_existing = any((s.get("html_s3_key") or "").strip() for s in sources)
    expects = bool(state.get("expects_slide_refinement"))

    if not has_existing:
        kind = "edit" if expects else "new"
        result = {
            "kind": kind,
            "scope": _scope(msg) if kind == "edit" else None,
            "confidence": "high" if not expects else "medium",
            "requires_existing_html": kind == "edit",
            "reason": "api expects refinement but no html sources" if expects else "no existing html",
        }
        out: dict[str, object] = {"intent_result": result, "is_refinement": False}
        if expects:
            from app.nodes.finalize_messages import JOB_FAILURE_REFINEMENT_CONTEXT
            from app.state import copy_errors

            out["refinement_context_unavailable"] = True
            out["errors"] = copy_errors(state) + [JOB_FAILURE_REFINEMENT_CONTEXT]
        return out

    if _NEW_HINT.search(msg):
        return {
            "intent_result": {
                "kind": "new",
                "scope": None,
                "confidence": "high",
                "requires_existing_html": False,
                "reason": "new-post wording with prior html available",
            },
            "is_refinement": False,
        }

    has_edit_hint = bool(
        _EDIT_HINT.search(msg)
        or _COPY_HINT.search(msg)
        or _LAYOUT_HINT.search(msg)
        or _VISUAL_HINT.search(msg)
    )
    if not has_edit_hint:
        return {
            "intent_result": {
                "kind": "new",
                "scope": None,
                "confidence": "medium",
                "requires_existing_html": False,
                "reason": "prior html available but no edit wording",
            },
            "is_refinement": False,
        }

    scope = _scope(msg)
    return {
        "intent_result": {
            "kind": "edit",
            "scope": scope,
            "confidence": "medium",
            "requires_existing_html": True,
            "reason": "prior html available and no explicit new-post wording",
        },
        "is_refinement": True,
        "refinement_scope": scope,
    }


def route_after_intent(state: AgentState) -> str:
    if state.get("refinement_context_unavailable"):
        return "fail"
    result = state.get("intent_result") or {}
    return "edit" if result.get("kind") == "edit" else "new"
