"""Generate carousel HTML via LLM using delimited slide blocks."""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import PROMPTS_DIR, get_settings
from app.state import AgentState

logger = logging.getLogger(__name__)


def _read_generate_prompt() -> str:
    path = PROMPTS_DIR / "generate_slides.md"
    return path.read_text(encoding="utf-8")


def generate_slides(state: AgentState) -> dict:
    logger.info("node=generate_slides job_id=%s", state.get("job_id"))
    settings = get_settings()
    system = _read_generate_prompt()
    profile = state.get("profile_text") or ""
    brief = state.get("optimized_brief") or ""
    user_content = f"{profile}\n\n---\n\nBrief otimizado:\n{brief}"

    llm = ChatOpenAI(
        api_key=settings.openai_api_key,
        model="gpt-4o-mini",
        max_tokens=4000,
    )
    msg = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=user_content),
        ]
    )
    raw = (msg.content or "").strip() if hasattr(msg, "content") else str(msg)
    return {"raw_slide_output": raw}
