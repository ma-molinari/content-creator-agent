# Relatório de validação — `medo-abandono-migalhas`

**Perfil:** `instagram-audits/2026-04-07-stephaniefalanque/`  
**Referência:** `AUDIT.md` (rosa/magenta como acento, preto/off-white, lockup consistente; tom PT-BR, jovens adultas).  
**Layout:** alinhado ao carrossel de referência `04_posts/p005_carousel_slide01–05.png` (barra `@handle // função`, magenta `#e02d8c`, rosa poeira para caixas secundárias, slides “foto” com grão simulado, slide editorial com caixa tipo balão, faixas por linha, bloco escuro no CTA final).

**Pipeline:** `node scripts/export-slides.js --validate` → `slide-XX-preview.jpg` (reexecutado após atualização de layout).

---

## Critérios globais

| Critério | Resultado | Notas |
|----------|-----------|--------|
| Paleta | **pass** | Magenta vibrante + rosa poeira + charcoal, coerente com amostra p005 e audit. |
| Lockup de marca | **pass** | `@stephaniefalanque` · `//` · Psicóloga de Jovens Adultas no topo, padrão horizontal do feed de referência. |
| Zona segura (~276px inferior) | **pass** | Blocos de texto principais e “Salva…” acima da faixa; numeração `bottom: 292px`. |
| Estilo visual | **pass** | Trocou colagem fitas/estrelas por sistema p005; tipografia Montserrat (Google Fonts). |
| Tom | **pass** | Copy original do tema preservada (ajustes mínimos no slide 2 para preencher linhas editoriais). |

---

## Por slide

### Slide 01 — Hook
- **pass** — Fundo “foto” com overlay + grão; faixas magenta/rosa inclinadas; kicker branco; marca clara no topo.

### Slide 02 — Problema
- **pass** — Fundo papel `#ebe8e6`; headline em caixa magenta com cauda (balão); linhas alternadas texto / caixa / cutouts com emoji (substitutos leves às fotos recortadas do p005).

### Slide 03 — Agitação
- **pass** — Lavagem rosa + faixas por linha (caps); caixa escura semitransparente para o parágrafo de apoio; label “Agitação (com carinho)”.

### Slide 04 — Reenquadramento
- **pass** — Papel neutro; título + caixa rosa (destaque) + parágrafo longo; sem bullets inventados — texto fiel ao slide original.

### Slide 05 — Passos
- **pass** — Título em caps; bullets com • magenta; nota em itálico sobre terapia preservada.

### Slide 06 — CTA
- **pass** — Faixas magenta tipo p005 slide 5; barra charcoal com pergunta + convite a comentar; hint de salvar acima do bloco.

---

## Resumo

**Pronto para revisão humana (HTML + previews).** Export final `slide-XX.jpg` só após confirmação explícita no chat (*Deseja exportar os slides em JPG?*).
