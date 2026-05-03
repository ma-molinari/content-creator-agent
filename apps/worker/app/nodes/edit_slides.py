"""Edit existing carousel HTML via LLM (same output contract as generate_slides)."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings, read_prompt_md
from app.generate_slides_tokens import compute_max_output_tokens
from app.llm_messages import langchain_message_text
from app.nodes.generate_slides import _count_instruction, _retry_feedback
from app.sanitize import sanitize_brief_output
from app.state import AgentState

logger = logging.getLogger(__name__)

_MAX_TOKENS_RETRY_HINT = 800


async def edit_slides(state: AgentState) -> dict[str, object]:
    logger.info("node=edit_slides job_id=%s", state.get("job_id"))
    settings = get_settings()
    system = read_prompt_md("edit_slides.md")
    profile = state.get("profile_text") or ""
    brief = sanitize_brief_output(state.get("optimized_brief") or "")
    requested = state.get("requested_slide_count")
    max_tokens = compute_max_output_tokens(
        requested if isinstance(requested, int) else None,
        settings,
    )
    if int(state.get("retry_count") or 0) > 0 or int(state.get("design_retry_count") or 0) > 0:
        max_tokens = min(max_tokens + _MAX_TOKENS_RETRY_HINT, settings.generate_slides_max_tokens_cap)

    slides_block = "\n\n".join(
        f"<!-- {s.get('filename') or 'slide.html'} -->\n{s.get('html') or ''}"
        for s in (state.get("existing_slide_html") or [])
    )
    user_content = (
        "<perfil_usuario>\n"
        f"{profile}\n"
        "</perfil_usuario>\n\n"
        "<brief_otimizado>\n"
        f"{brief}\n"
        "</brief_otimizado>\n\n"
        "<slides_existentes>\n"
        f"{slides_block}\n"
        "</slides_existentes>\n\n"
        "Instrução do usuário:\n"
        f"{state.get('raw_message') or ''}"
    )
    user_content += _count_instruction(requested if isinstance(requested, int) else None)
    if "REFERÊNCIAS_VISUAIS" in profile:
        user_content += (
            "\n\n---\n\n**⚠ Referências visuais obrigatórias:** "
            "`<perfil_usuario>` contém `## REFERÊNCIAS_VISUAIS (resumo)`. "
            "Preserve e reflita paleta, accent e ritmo ao editar."
        )
    user_content += _retry_feedback(state.get("errors"))

    logger.info(
        "node=edit_slides job_id=%s max_tokens=%s requested_slide_count=%s",
        state.get("job_id"),
        max_tokens,
        requested,
    )
    llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model=settings.openai_chat_model,
        max_tokens=max_tokens,
    )
    msg = await llm.ainvoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=user_content),
        ]
    )
    raw = langchain_message_text(msg)
    return {"raw_slide_output": raw}
