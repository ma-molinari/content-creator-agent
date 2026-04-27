"""Optimize user message into a structured brief using the LLM."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import PROMPTS_DIR, get_settings
from app.parse_optimize_output import split_optimize_response
from app.state import AgentState

logger = logging.getLogger(__name__)


def _read_optimize_prompt() -> str:
    path = PROMPTS_DIR / "optimize_prompt.md"
    return path.read_text(encoding="utf-8")


def optimize_prompt(state: AgentState) -> dict:
    logger.info("node=optimize_prompt job_id=%s", state.get("job_id"))
    settings = get_settings()
    system = _read_optimize_prompt()
    profile = state.get("profile_text") or ""
    raw = state.get("raw_message") or ""
    reprompt = (state.get("reprompt_context") or "").strip()
    requested = state.get("requested_slide_count")
    user_parts = [
        "<perfil_usuario>",
        profile,
        "</perfil_usuario>",
        "",
        "<pedido_usuario>",
        raw,
        "</pedido_usuario>",
    ]
    if isinstance(requested, int):
        user_parts.extend(
            [
                "",
                f"**Quantidade de slides (obrigatória):** o carrossel deve ter **exatamente {requested} slides** — "
                "o brief e a estrutura narrativa devem respeitar esse N (nem a mais, nem a menos).",
            ]
        )
    if reprompt:
        user_parts.extend(["", "<contexto_anterior>", reprompt, "</contexto_anterior>"])
    user_content = "\n".join(user_parts)

    llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_chat_model,
        max_tokens=4000,
    )
    msg = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=user_content),
        ]
    )
    text = (msg.content or "").strip() if hasattr(msg, "content") else str(msg)
    brief, user_msg = split_optimize_response(text)
    out: dict = {"optimized_brief": brief}
    if user_msg:
        out["assistant_text"] = user_msg
    return out
