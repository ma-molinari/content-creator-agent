# Context checklist — expanded reference

Companion to [SKILL.md](SKILL.md). Use for “too vague?” judgment and example responses.


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
