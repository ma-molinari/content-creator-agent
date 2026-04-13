"""Optimize user message into a structured brief using the LLM."""

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import PROMPTS_DIR, get_settings
from app.state import AgentState


def _read_optimize_prompt() -> str:
    path = PROMPTS_DIR / "optimize_prompt.md"
    return path.read_text(encoding="utf-8")


def optimize_prompt(state: AgentState) -> dict:
    settings = get_settings()
    system = _read_optimize_prompt()
    profile = state.get("profile_text") or ""
    raw = state.get("raw_message") or ""
    reprompt = (state.get("reprompt_context") or "").strip()
    user_parts = [profile, "---", "Pedido do usuário:", raw]
    if reprompt:
        user_parts.extend(["---", "Contexto anterior do chat:", reprompt])
    user_content = "\n\n".join(user_parts)

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
    text = (msg.content or "").strip() if hasattr(msg, "content") else str(msg)
    return {"optimized_brief": text}
