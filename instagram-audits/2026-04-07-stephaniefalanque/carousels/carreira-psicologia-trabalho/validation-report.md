# Relatório de validação — `carreira-psicologia-trabalho`

**Perfil:** `instagram-audits/2026-04-07-stephaniefalanque/`  
**Referência visual:** `AUDIT.md` (rosa/magenta, preto/off-white, colagem contemporânea, lockup `@handle // função`, terapia acessível).  
**Planejamento editorial:** `BRAND.md` (tom segunda pessoa, micro-ações, CTA explícito, disclaimer sem substituir terapia).

**Pipeline:** `node scripts/export-slides.js --validate instagram-audits/2026-04-07-stephaniefalanque/carousels/carreira-psicologia-trabalho` → `slide-XX-preview.jpg`.

**Última passagem (layout):** tokens de espaçamento/tipografia em `slides.css` (grid 4px, escala de texto); estilos por slide consolidados no CSS partilhado; `tag--on-wash` em slides 03 e 06 para contraste legível no fundo claro (antes `.slide--photo .tag` forçava branco). Previews regenerados com Playwright.

---

## Critérios globais

| Critério | Resultado | Notas |
|----------|-----------|--------|
| Paleta | **pass** | Magenta `#e02d8c`, rosa poeira, papel e charcoal alinhados a `BRAND.md` / carrosséis irmãos. |
| Lockup de marca | **pass** | `@stephaniefalanque` · `//` · Psicóloga de Jovens Adultas no topo em todos os slides. |
| Zona segura (~276–300px inferior) | **pass** | Miolo e numeração (`bottom: 292px`) acima da faixa de UI; CTA final em barra charcoal ancorada acima do limite. |
| Centralização (miolo esparso) | **pass** | `slide__body-centered` com `justify-content: center` nos slides com poucas linhas (01, 03, 06). |
| Tom e ética | **pass** | Psicoeducação; slide 05 e legenda com aviso de não substituir acompanhamento; burnout sem culpabilizar. |

---

## Por slide

### Slide 01 — Hook
- **pass** — Fundo escuro com lavagem magenta + grão; faixas inclinadas; kicker sobre carreira/produtividade; lockup claro (`brand-bar--light`).

### Slide 02 — Síndrome do impostor
- **pass** — Papel; faixas caps; corpo legível; tag “1 · Alta performance”.

### Slide 03 — Burnout vs. cansaço
- **pass** — Pink-wash + três faixas + caixa escura para corpo; tag “2 · Pressão e ambiente” com `tag--on-wash` (texto escuro legível); convite a escuta clínica sem diagnosticar.

### Slide 04 — Procrastinação
- **pass** — Papel; explicação + callout rosa “Hack gentil”; tag “3 · Estudo e home office”.

### Slide 05 — Próximos passos
- **pass** — Bullets com âncora magenta; disclaimer itálico; hierarquia caps + lista.

### Slide 06 — CTA
- **pass** — Faixas pergunta; bloco charcoal com comentário 1/2/3, menção LinkedIn/Stories, bio e “Salva…”; label “Quero te ouvir” com `tag--on-wash` (sem inline styles).

---

## Resumo

**Pronto para revisão humana (HTML + previews).** Export final `slide-XX.jpg` só após resposta afirmativa explícita no chat à pergunta: *Deseja exportar os slides em JPG?*
