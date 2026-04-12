# Context checklist — expanded reference

Companion to [SKILL.md](SKILL.md). Use for “too vague?” judgment and example responses.

---

## Vague vs acceptable (by criterion)

| Criterion | Too vague | Acceptable |
|-----------|-----------|------------|
| Objective | “Quero engajar” | “Educar sobre sinais de burnout sem medicalizar; objetivo é salvar o post e DM para triagem” |
| Audience | “Mulheres” | “Mulheres 28–45, CLT, primeira linha de gestão; já seguem conteúdo de produtividade” |
| Substance | “Fale sobre ansiedade” | “3 mitos vs 3 verdades; mitos: ‘ansiedade é frescura’, ‘remédio vicia sempre’, ‘relaxar resolve tudo’; verdades alinhadas a psicoeducação, sem diagnóstico” |
| Language / tone | “Natural” | “PT-BR, tom acolhedor e direto como no `AUDIT.md` / `BRAND.md` do audit de @handle (se existir); evitar gírias de TikTok” |
| Platform / format | “Um negócio pro Insta” | “Legenda até ~2.200 caracteres com CTA para comentário” **or** “Carrossel 6 slides no repo, formato 9:16” |
| Carousel profile | “Faz aí” | “Perfil `2026-04-07-stephaniefalanque`; pasta `instagram-audits/.../carousels/ansiedade-mitos-verdades/`; li o `AUDIT.md` deste audit; se existir `BRAND.md` na raiz do audit, li e usei no planejamento” |
| Interactive element (Stories) | “Coloca uma enquete aí” | “Poll: ‘Você já fez X?’ com opções Sim / Ainda não; frame 3 da sequência” |
| Engagement goal (Stories) | “Quero engajar” | “Retenção: aprofundar relação com seguidoras existentes via question box sobre dúvidas de [tema]” |
| Restrictions (sensitive) | (omitted) | “Não prometer cura; incluir aviso de que não substitui acompanhamento profissional” |

---

## Example A — Insufficient prompt

**User:** “Cria um carrossel legal sobre terapia.”

**Agent (expected):** Brief summary: carrossel sobre terapia, sem ângulo nem público definidos.

1. **Objetivo:** É para educar (mitos/verdades), engajar (história), ou converter (agendar sessão)?
2. **Público:** Quem é a pessoa ideal? Idade, contexto, nível de familiaridade com terapia?
3. **Substância:** Quais 3–6 mensagens ou slides devem existir? Tem dados, frases ou tópicos obrigatórios?
4. **Tom e idioma:** PT-BR? Formal, informal, alinhado a qual perfil — há `AUDIT.md` em `instagram-audits/<data>-<handle>/`?
5. **Perfil/pasta:** Qual handle ou caminho da pasta do carrossel no repo para eu ler o audit?

*Quando você responder, continuo com a criação.*

(No HTML, no `export-slides.js` until gate passes.)

---

## Example B — Sufficient prompt

**User:** “Carrossel 6 slides, PT-BR, tom do audit da Stephanie (`instagram-audits/2026-04-07-stephaniefalanque/`). Tema: 3 mitos e 3 verdades sobre ansiedade; público mulheres adultas leigas; objetivo psicoeducação e salvar; sem prometer cura; CTA comentar qual mito reconheceu.”

**Agent (expected):** Confirm gate OK in one short line, then attach `@.cursor/rules/marketing/marketing-carousel-growth-engine.md`, read `AUDIT.md` and, if present, **`BRAND.md`** in the same audit folder for planning (pilares, tom, CTAs), implement under the correct `carousels/<slug>/`, run **Phase D** of the skill: `export-slides.js --validate`, inspect each preview against the **parent folder** `AUDIT.md` (identidade visual) and narrative/tom against **`BRAND.md`** when it exists, write `validation-report.md` — and **ask** before `--export --confirm` (Phase E).

---

## Example C — Post with sensitive theme, missing safeguards

**User:** “Legenda sobre como sair da depressão sozinho.”

**Agent (expected):** Flag sensitive topic; require restrictions (no promise of self-cure, encourage professional help), plus objective, audience, and tone. Do not draft the caption until answered.

---

## Example D — Stories, insufficient prompt

**User:** “Faz umas stories bonitas sobre autocuidado.”

**Agent (expected):** Brief summary: Stories sobre autocuidado, sem arco nem formato interativo definidos.

1. **Objetivo da peça:** Educar, gerar DM, reter quem já segue, ou alcançar novas contas?
2. **Público:** Quem deve ver a sequência? Tom alinhado a algum `AUDIT.md` / perfil?
3. **Substância:** Quantos frames (3–7)? Quais mensagens ou gancho → contexto → fechamento?
4. **Elemento interativo obrigatório:** Qual tipo — poll, quiz, question box, emoji slider — e em qual frame, com copy exata das opções ou pergunta?
5. **Meta de engajamento:** Retenção (relacionamento com seguidoras) vs descoberta (alcance) — como isso muda o opener e o CTA?

*Quando você responder, continuo com a criação.*

(No roteiro completo por frame até o gate passar.)
