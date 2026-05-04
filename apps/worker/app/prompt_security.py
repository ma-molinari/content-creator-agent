"""Deterministic validation of user-controlled prompt fields before LLM steps.

Reason codes are logged internally; user-facing copy is fixed (see finalize path).
Patterns are iterated based on abuse metrics — extend with care for false positives."""

from __future__ import annotations

import re
import unicodedata

from app.config import get_settings
from app.state import AgentState

# Fixed pt-BR message appended to state errors when validation rejects (no echo of input).
USER_PROMPT_REJECT_MESSAGE = (
    "Seu pedido não pôde ser processado por políticas de segurança. "
    "Revise o texto e tente novamente."
)

# Internal reason codes for logs (rule=<code>), not exposed to end users.
REASON_MAX_LENGTH = "max_length"
REASON_PROFILE_MAX_LENGTH = "profile_max_length"
REASON_CONTROL_CHARS = "control_chars"
REASON_DELIMITER_TAG = "delimiter_tag"
REASON_SLIDE_MARKER = "slide_marker"
REASON_INJECTION_PHRASE = "injection_phrase"

# Covers API max persisted profile: 20k bytes per audit and brand (profile/sanitize.go);
# load_profile adds "## AUDIT" / "## BRAND" headers. Count is Unicode code points.
PROFILE_TEXT_MAX_CHARS = 48_000

# Profile audit+brand blob exceeds PROFILE_TEXT_MAX_CHARS (Unicode code points).
USER_PROFILE_TEXT_TOO_LONG_MESSAGE = (
    "O texto combinado de auditoria e de marca no seu perfil ultrapassou o limite de "
    f"{PROFILE_TEXT_MAX_CHARS} caracteres. Encurte um ou ambos os campos e tente novamente."
)

# Substrings that must not appear inside raw_message (pipeline/XML escapes).
_DELIMITER_SNIPPETS = (
    "</perfil_usuario>",
    "<perfil_usuario>",
    "</pedido_usuario>",
    "<pedido_usuario>",
    "<contexto_anterior>",
    "</contexto_anterior>",
    "<brief_otimizado>",
    "</brief_otimizado>",
    "</system>",
    "<system>",
)

_SLIDE_MARKER_RES = (
    re.compile(r"###\s*SLIDE_FILE", re.IGNORECASE),
    re.compile(r"###\s*END_SLIDE\s*###", re.IGNORECASE),
)

# High-confidence jailbreak / instruction-override phrases (pt/en). Tune when monitoring false positives.
_INJECTION_RES = (
    re.compile(
        r"\b(?:ignore|disregard)\s+(?:all\s+|any\s+|previous\s+|prior\s+|your\s+|the\s+)*"
        r"(?:instructions|rules|guidelines)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:desconsiderar|ignorar)\s+(?:todas\s+as\s+|todas\s+|as\s+|suas\s+)?instruções\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\breveal\s+(?:your\s+|the\s+)?(?:hidden\s+)?system\s+prompt\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\brevel(?:ar)?\s+(?:o\s+|seu\s+)?(?:prompt\s+)?(?:de\s+sistema)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\brevel(?:ar)?\s+(?:o\s+|seu\s+|nosso\s+)?system\s+prompt\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\byou\s+(?:have\s+)?(?:no\s+|zero\s+)?(?:ethical\s+|safety\s+|content\s+)?restrictions\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bforget\s+(?:everything|all)\s+(?:above|before|prior)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\besque(?:ça|ca)\s+tudo\s+(?:o\s+)?(?:que\s+)?(?:foi\s+dito|vimos)\s+antes\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bnew\s+system\s+prompt\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\boverride\s+(?:the\s+|your\s+)?system\s+prompt\b",
        re.IGNORECASE,
    ),
)


def _has_disallowed_controls(text: str) -> bool:
    for ch in text:
        if ch in "\n\r\t":
            continue
        if unicodedata.category(ch) == "Cc":
            return True
    return False


def _validate_prompt_content_rules(text: str) -> tuple[bool, str | None]:
    """Delimiter tags, slide markers, jailbreak phrases, disallowed controls (no length)."""
    if _has_disallowed_controls(text):
        return False, REASON_CONTROL_CHARS

    haystack = text.lower()
    for snippet in _DELIMITER_SNIPPETS:
        if snippet.lower() in haystack:
            return False, REASON_DELIMITER_TAG

    for rx in _SLIDE_MARKER_RES:
        if rx.search(text):
            return False, REASON_SLIDE_MARKER

    for rx in _INJECTION_RES:
        if rx.search(text):
            return False, REASON_INJECTION_PHRASE

    return True, None


def validate_profile_text(text: str) -> tuple[bool, str | None]:
    """Defense-in-depth for audit+brand blob (same structural rules as user message, stricter length)."""
    if len(text) > PROFILE_TEXT_MAX_CHARS:
        return False, REASON_PROFILE_MAX_LENGTH
    return _validate_prompt_content_rules(text)


def validate_user_prompt(state: AgentState) -> tuple[bool, str | None]:
    """Return (ok, reason_code). reason_code is for logging only when ok is False."""
    settings = get_settings()
    raw = state.get("raw_message") or ""

    if len(raw) > settings.user_prompt_max_chars:
        return False, REASON_MAX_LENGTH

    ok, reason = _validate_prompt_content_rules(raw)
    if not ok:
        return False, reason

    return True, None


def validate_prompt_security_bundle(state: AgentState) -> tuple[bool, str | None]:
    """Validate user message and loaded profile_text (after load_profile)."""
    ok, reason = validate_user_prompt(state)
    if not ok:
        return False, reason
    profile = (state.get("profile_text") or "").strip()
    if not profile:
        return True, None
    return validate_profile_text(profile)
