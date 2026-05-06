"""Format `<anexos_do_usuario>` blocks for downstream LLM user messages."""

from __future__ import annotations

import html

from app.state import AgentState


def format_user_attachments_block(state: AgentState) -> str:
    keys = state.get("user_attachment_s3_keys") or []
    if not keys:
        return ""
    urls = state.get("user_attachment_signed_urls") or []
    descs = state.get("user_attachment_descriptions") or []
    mimes = state.get("user_attachment_mime_types") or []
    intent = state.get("user_attachment_intent") or "cover_default"

    parts = [f'<anexos_do_usuario count="{len(keys)}" intent="{html.escape(intent, quote=True)}">']
    for i in range(len(keys)):
        raw_url = urls[i] if i < len(urls) else ""
        url_attr = html.escape(raw_url, quote=True)
        desc = html.escape(descs[i], quote=False) if i < len(descs) else ""
        mime = mimes[i] if i < len(mimes) else "image/jpeg"
        mime_safe = html.escape(mime, quote=True)
        parts.append(f'  <imagem n="{i + 1}" url="{url_attr}" mime="{mime_safe}">{desc}</imagem>')
    parts.append("</anexos_do_usuario>")
    parts.append("")
    parts.append("ORIENTAÇÃO DE USO:")
    if intent == "explicit":
        parts.append("- Siga estritamente a instrução do utilizador em <raw_message>.")
    else:
        parts.append("- Use IMAGEM 1 como visual dominante do slide 1 (capa).")
    parts.append("- SEMPRE referenciar via URL completa em src= ou background-image: url(...).")
    return "\n".join(parts)
