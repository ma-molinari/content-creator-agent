"""Generate carousel HTML via LLM using delimited slide blocks."""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import PROMPTS_DIR, get_settings
from app.generate_slides_tokens import compute_max_output_tokens
from app.sanitize import sanitize_brief_output  # noqa: F401 (re-exported for tests)
from app.state import AgentState

logger = logging.getLogger(__name__)

_MAX_TOKENS_RETRY_HINT = 800


def _read_generate_prompt() -> str:
    path = PROMPTS_DIR / "generate_slides.md"
    return path.read_text(encoding="utf-8")


def _retry_feedback(errors: list[str] | None) -> str:
    if not errors:
        return ""
    # Last errors first; keep parse/validation messages for the model.
    relevant = [e for e in errors if "parse_validate" in (e or "")]
    lines = (relevant or errors)[-3:]
    if not lines:
        return ""
    return "\n\n---\n\nCorreção (tentativa anterior):\n" + "\n".join(lines)


def _count_instruction(requested: int | None) -> str:
    if requested is None:
        return ""
    n = int(requested)
    return (
        f"\n\n---\n\n**Quantidade obrigatória:** gere **exatamente {n}** blocos `###SLIDE_FILE:...###` "
        f"… `###END_SLIDE###` (um HTML completo por bloco, nomes `slide_01.html` … `slide_{n:02d}.html`).\n"
    )


def generate_slides(state: AgentState) -> dict:
    logger.info("node=generate_slides job_id=%s", state.get("job_id"))
    settings = get_settings()
    system = _read_generate_prompt()
    profile = state.get("profile_text") or ""
    brief = sanitize_brief_output(state.get("optimized_brief") or "")
    requested = state.get("requested_slide_count")
    max_tokens = compute_max_output_tokens(
        requested if isinstance(requested, int) else None,
        settings,
    )
    # Retries after truncation may need more headroom.
    if int(state.get("retry_count") or 0) > 0:
        max_tokens = min(max_tokens + _MAX_TOKENS_RETRY_HINT, settings.generate_slides_max_tokens_cap)

    user_content = (
        "<perfil_usuario>\n"
        f"{profile}\n"
        "</perfil_usuario>\n\n"
        "<brief_otimizado>\n"
        f"{brief}\n"
        "</brief_otimizado>"
    )
    user_content += _count_instruction(requested if isinstance(requested, int) else None)
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
    msg = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=user_content),
        ]
    )
    raw = (msg.content or "").strip() if hasattr(msg, "content") else str(msg)
    return {"raw_slide_output": raw}
