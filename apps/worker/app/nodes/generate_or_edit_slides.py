"""Generate or edit slides using a structured JSON + HTML contract."""

from __future__ import annotations

import json
import logging
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.config import get_settings
from app.generate_slides_tokens import MAX_TOKENS_RETRY_HINT, compute_max_output_tokens
from app.llm_messages import langchain_message_text
from app.state import AgentState

logger = logging.getLogger(__name__)

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)

_SYSTEM = """Você é diretor de arte editorial e front-end designer para posts/carrosséis Instagram.
Responda SOMENTE JSON válido, sem markdown.

Schema obrigatório:
{"assistant_text":"texto curto para o chat","slides":[{"filename":"slide_01.html","slide_number":1,"html":"<html>...</html>","used_attachment_ids":["..."]}],"layout_notes":"...","attachment_usage":[{"attachment_id":"...","slide_number":1,"usage":"..."}]}

Contrato técnico:
- Gere um documento HTML completo por slide, CSS autocontido, canvas fixo 1080x1350, sem JS.
- Use Google Fonts como único recurso remoto. Para imagens anexadas, use SOMENTE os render_ref fornecidos em attachment_requirements.
- Cada slide precisa ter `body{width:1080px;height:1350px;margin:0;overflow:hidden}` e layout em grid/flex.
- Use Plus Jakarta Sans por padrão, contraste AA, safe area e texto legível em mobile.

Direção de design:
- Crie posts premium, prontos para Instagram: composição editorial, hierarquia forte, respiro controlado, contraste limpo, ritmo visual entre slides e CTA claro no final.
- Evite aparência de wireframe/template: nada de caixas vazias, placeholders, mockups pequenos perdidos, labels como "imagem em anexo" ou "visual aqui".
- Cada slide deve ter uma ideia visual dominante e copy útil. Use palavras-chave em destaque, superfícies com sombra/blur/overlay quando ajudarem leitura, e paleta coerente com profile_text/profile_overview.
- Se houver anexo obrigatório, ele NÃO é decoração nem referência abstrata: deve entrar como material visual real do slide.

Uso de imagens anexadas:
- Cada item em generation_plan.attachment_requirements tem `id`, `render_ref`, `description`, `required_slide_number`, `role` e `composition_rule`.
- Quando `required_slide_number` existir, o slide alvo DEVE conter a imagem real usando o render_ref exato em `<img src="attachment://...">` ou `background-image:url("attachment://...")`.
- A imagem anexada deve ser parte visível do design: hero recortado, fundo com overlay, moldura editorial grande, textura/foto integrada ou split visual expressivo.
- Para slide de capa com anexo, reserve normalmente 45% a 80% do canvas para a imagem ou use-a fullscreen com overlay. Não use miniatura pequena.
- Se usar texto sobre imagem, aplique overlay/gradiente/blur para legibilidade. Não esconda a imagem atrás de painéis opacos.
- Preencha `used_attachment_ids` no slide e `attachment_usage` explicando onde a imagem entrou.
- Nunca substitua a imagem por uma descrição textual ou por placeholder.

Modo de edição:
- Quando `generation_plan.mode` for `edit`, devolva EXATAMENTE o mesmo número de slides de `existing_slides`.
- Em `edit`, preserve os mesmos `filename` e `slide_number` dos slides existentes, apenas atualizando o HTML.
- Em `edit`, trate `generation_plan.raw_message` como instrução de patch sobre os slides existentes, nunca como tema para novo conteúdo.
- Se o pedido falar de layout/visual, preserve o conteúdo textual e reorganize composição, hierarquia, tipografia, espaçamento e superfícies.
- Se o pedido falar de layout/visual, não crie slides explicando a mudança pedida e não troque o assunto central do carrossel.
"""


def _extract_json(text: str) -> dict:
    raw = (text or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = _JSON_OBJECT_RE.search(raw)
        if not m:
            raise
        return json.loads(m.group(0))


def _retry_feedback(state: AgentState) -> list[str]:
    report = state.get("validation_report") or {}
    messages = list(report.get("actionable_messages") or [])
    if not messages:
        messages = [
            e
            for e in (state.get("errors") or [])
            if any(prefix in e for prefix in ("slide_package:", "validate_design:", "attachment_usage:"))
        ]
    return messages[-8:]


async def generate_or_edit_slides(state: AgentState) -> dict[str, object]:
    logger.info("node=generate_or_edit_slides job_id=%s", state.get("job_id"))
    settings = get_settings()
    plan = state.get("generation_plan") or {}
    requested = state.get("requested_slide_count")
    max_tokens = compute_max_output_tokens(
        requested if isinstance(requested, int) else None,
        settings,
    )
    retry_count = int(state.get("retry_count") or 0) + int(state.get("design_retry_count") or 0)
    if retry_count > 0:
        max_tokens = min(max_tokens + MAX_TOKENS_RETRY_HINT, settings.generate_slides_max_tokens_cap)

    existing = [
        {"filename": s.get("filename"), "html": s.get("html")}
        for s in (state.get("existing_slide_html") or [])
    ]
    payload = {
        "generation_plan": plan,
        "profile_text": state.get("profile_text") or "",
        "existing_slides": existing,
        "retry_feedback": _retry_feedback(state),
    }
    kwargs = {
        "api_key": settings.openai_api_key,
        "model": settings.openai_chat_model,
        "max_tokens": max_tokens,
    }
    if plan.get("mode") == "edit":
        kwargs["temperature"] = 0
    llm = ChatOpenAI(**kwargs)
    msg = await llm.ainvoke(
        [
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
        ]
    )
    raw = langchain_message_text(msg)
    try:
        package = _extract_json(raw)
    except Exception as exc:
        errors = list(state.get("errors") or [])
        errors.append(f"slide_package: JSON inválido retornado pelo modelo: {exc!s}")
        return {
            "raw_slide_output": raw,
            "slide_package": {"assistant_text": "", "slides": []},
            "slides_html": [],
            "errors": errors,
        }
    return {
        "raw_slide_output": raw,
        "slide_package": package,
        "assistant_text": str(package.get("assistant_text") or "").strip(),
    }
