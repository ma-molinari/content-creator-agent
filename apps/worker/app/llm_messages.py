"""Normalize LangChain message outputs to plain strings."""

from __future__ import annotations


def langchain_message_text(message: object) -> str:
    """Return trimmed text content from AIMessage/BaseMessage outputs (text completions)."""
    if not hasattr(message, "content"):
        return str(message).strip()
    content = getattr(message, "content")
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    return str(content).strip()
