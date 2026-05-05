"""Generate carousel HTML via LLM using delimited slide blocks."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings, read_prompt_md
from app.generate_slides_tokens import MAX_TOKENS_RETRY_HINT, compute_max_output_tokens
from app.llm_messages import langchain_message_text
from app.sanitize import sanitize_brief_output
from app.state import AgentState

logger = logging.getLogger(__name__)


def _retry_feedback(errors: list[str] | None) -> str:
    if not errors:
        return ""
    relevant = [
        e
        for e in errors
        if "parse_validate:" in (e or "")
        or "design_validate:" in (e or "")
        or "copy_preservation:" in (e or "")
    ]
    lines = relevant[-8:] if relevant else []
    if not lines:
        return ""
    bullets = "\n".join(f"- {line}" for line in lines)
    return (
        "\n\n---\n\n**Correções necessárias (saída anterior — cumpra na íntegra):**\n"
        f"{bullets}\n\n"
        "Regenerar **todos** os blocos `###SLIDE_FILE:` … `###END_SLIDE###` pedidos; cada slide deve ser "
        "um HTML completo com `<html>` e `</html>`. Não omita arquivos listados como ausentes; corrija HTML "
        "marcado como inválido e **as regras de design** indicadas acima (CSS autocontido, Plus Jakarta Sans/GF, viewport 1080×1350px, sem URLs remotas nem JS)."
    )


def _count_instruction(requested: int | None) -> str:
    if requested is None:
        return ""
    n = int(requested)
    return (
        f"\n\n---\n\n**Quantidade obrigatória:** gere **exatamente {n}** blocos `###SLIDE_FILE:...###` "
        f"… `###END_SLIDE###` (um HTML completo por bloco, nomes `slide_01.html` … `slide_{n:02d}.html`).\n"
    )


async def generate_slides(state: AgentState) -> dict[str, object]:
    logger.info("node=generate_slides job_id=%s", state.get("job_id"))
    settings = get_settings()
    system = read_prompt_md("generate_slides.md")
    profile = state.get("profile_text") or ""
    brief = sanitize_brief_output(state.get("optimized_brief") or "")
    requested = state.get("requested_slide_count")
    max_tokens = compute_max_output_tokens(
        requested if isinstance(requested, int) else None,
        settings,
    )
    # Retries after truncation may need more headroom.
    if int(state.get("retry_count") or 0) > 0 or int(state.get("design_retry_count") or 0) > 0:
        max_tokens = min(max_tokens + MAX_TOKENS_RETRY_HINT, settings.generate_slides_max_tokens_cap)

    user_content = (
        "<perfil_usuario>\n"
        f"{profile}\n"
        "</perfil_usuario>\n\n"
        "<brief_otimizado>\n"
        f"{brief}\n"
        "</brief_otimizado>"
    )
    user_content += _count_instruction(requested if isinstance(requested, int) else None)
    if "REFERÊNCIAS_VISUAIS" in profile:
        user_content += (
            "\n\n---\n\n**⚠ Referências visuais obrigatórias:** "
            "`<perfil_usuario>` contém `## REFERÊNCIAS_VISUAIS (resumo)`. "
            "O CSS de **cada slide** (paleta, accent, gradientes, sombras, ritmo claro/escuro) "
            "**deve refletir** esse resumo e a tradução do brief — "
            "não use look neutro genérico que ignore a paleta indicada."
        )
    user_content += _retry_feedback(state.get("errors"))

    logger.info(
        "node=generate_slides job_id=%s max_tokens=%s requested_slide_count=%s retry_count=%s",
        state.get("job_id"),
        max_tokens,
        requested,
        state.get("retry_count"),
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
