"""Optimize user message into a structured brief using the LLM."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings, read_prompt_md
from app.llm_messages import langchain_message_text
from app.parse_optimize_output import split_optimize_response
from app.state import AgentState

logger = logging.getLogger(__name__)


async def optimize_prompt(state: AgentState) -> dict[str, object]:
    logger.info("node=optimize_prompt job_id=%s", state.get("job_id"))
    settings = get_settings()
    system = read_prompt_md("optimize_prompt.md")
    profile = state.get("profile_text") or ""
    raw = state.get("raw_message") or ""
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
    user_content = "\n".join(user_parts)

    llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_chat_model,
        max_tokens=4000,
    )
    msg = await llm.ainvoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=user_content),
        ]
    )
    text = langchain_message_text(msg)
    brief, user_msg = split_optimize_response(text)
    out: dict[str, object] = {"optimized_brief": brief}
    if user_msg:
        out["assistant_text"] = user_msg
    return out
