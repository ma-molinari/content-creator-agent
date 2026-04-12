# Validation Report — burnout-disfuncao-executiva

**Carousel:** burnout-disfuncao-executiva  
**Profile:** @stephaniefalanque  
**Audit reference:** `instagram-audits/2026-04-07-stephaniefalanque/AUDIT.md` + `BRAND.md`  
**Validate run:** `node scripts/export-slides.js --validate` (2× — segunda passagem após correção de centralização nos slides 02 e 03)  
**Date:** 2026-04-09

---

## Checklist Geral

Critérios derivados do `AUDIT.md` e `BRAND.md`:

| Critério | Status |
|---|---|
| Paleta — magenta `#e02d8c`, off-white `#f2efec`, texto escuro `#1a1a1a` | ✅ pass |
| Lockup Variant A — barra topo `@STEPHANIEFALANQUE // PSICÓLOGA DE JOVENS ADULTAS` | ✅ pass |
| Zona segura inferior 276px — nenhum texto essencial abaixo | ✅ pass |
| Faixas magenta rotacionadas (assinatura da marca) | ✅ pass |
| Fonte Montserrat — pesos 500, 700, 800, 900 | ✅ pass |
| Hero ≥ 58px | ✅ pass (--t-hero: 64px) |
| Heading ≥ 43px | ✅ pass (--t-heading: 46px) |
| Body ≥ 34px | ✅ pass (--t-body: 34px; --t-body-sm: 28px para texto de apoio) |
| Caption ≥ 24px | ✅ pass (--t-caption: 24px; disclaimer 24px) |
| Piso absoluto ≥ 20px | ✅ pass (menor elemento: cta-label 20px) |
| Font weight ≥ 500 para body e acima | ✅ pass |
| Sem contador de slides nas imagens | ✅ pass |
| Design system documentado em `:root` antes dos slides | ✅ pass |
| Foto Unsplash — baixada localmente (`bg-burnout.jpg`, Tsimur Asayonak / Unsplash License) | ✅ pass |
| HTML self-contained (Google Fonts único recurso externo) | ✅ pass |
| Body 768×1376px, overflow hidden | ✅ pass |
| Layout via Flexbox (sem absolute para fluxo principal) | ✅ pass |
| Tom PT-BR, segunda pessoa, acolhimento + educação | ✅ pass |
| CTA explícito na legenda (DM, bio, salvar) | ✅ pass |
| Disclaimer clínico presente (slide 06) | ✅ pass |
| Sem caixas sólidas pretas/cinza opacas (vidro semi-transparente usado) | ✅ pass |

---

## Por Slide

### Slide 01 — Gancho (T1 Editorial Photo)
- **Preview:** `slide-01-preview.jpg` (216 KB — confirma foto carregada)
- **Paleta:** overlay escuro 55–88% sobre foto analógica; faixas magenta `#e02d8c`; callout glass dark
- **Lockup:** Variant A clara (`brand-bar--light`) no topo — ✅
- **Tipografia:** hero 64px nas faixas, body 34px no callout — ✅
- **Zona segura:** conteúdo termina bem acima dos 276px — ✅
- **Foto Unsplash:** visível através do overlay (slide 01 ~216 KB vs. off-white ~130 KB) — ✅
- **Tom:** kicker "Burnout & Disfunção Executiva" + gancho "Por que tarefas simples parecem montanhas?" — alinhado à voz da marca (acolhimento + nomeação do padrão)
- **Status: PASS**

### Slide 02 — Cansaço vs. Exaustão Emocional (T5 Light + cards)
- **Preview:** `slide-02-preview.jpg` (126 KB)
- **Paleta:** fundo off-white; card cansaço azul-acinzentado; card exaustão rosa magenta — ritmo visual contrastante ✅
- **Lockup:** Variant A escura — ✅
- **Centralização:** corrigida (removido `align-top`, flex center) — miolo bem balanceado entre brand bar e zona segura — ✅
- **Hierarquia:** kicker magenta → heading → 2 cards comparativos com ícones e texto de apoio — ✅
- **Conteúdo:** diferenciação clara entre "o descanso resolve" (cansaço) e "o descanso não resolve" (exaustão) — alinhado ao pilar "regulação e TCC/DBT" do BRAND.md
- **Status: PASS**

### Slide 03 — Paralisia: você quer mas não consegue começar (T5 + faixas)
- **Preview:** `slide-03-preview.jpg` (141 KB)
- **Paleta:** fundo off-white; 3 faixas magenta em sequência; callout glass claro; nota muted
- **Lockup:** Variant A escura — ✅
- **Centralização:** `justify-content: center` aplicado — conteúdo distribuído na área útil — ✅
- **Faixas:** 3 strips alternando -2°/+1.5° com sombra rosa — assinatura visual presente ✅
- **Validação emocional:** "Não é preguiça. É o sistema nervoso travado." — tom acolhedor sem diagnóstico — ✅
- **Status: PASS**

### Slide 04 — Por que o cérebro trava (T5 Light + painéis científicos)
- **Preview:** `slide-04-preview.jpg` (130 KB)
- **Paleta:** fundo off-white; painel TDAH rosa pale + borda magenta; painel Burnout azul pale + borda azul — diferenciação visual clara ✅
- **Lockup:** Variant A escura — ✅
- **Conteúdo:** explica dopamina (TDAH) e córtex pré-frontal (Burnout) em linguagem acessível — alinhado ao pilar "regulação e TCC/DBT" sem linguagem clínica fria ✅
- **Nota de intersecção:** "Podem acontecer juntos — e se reforçam." — humaniza e aumenta identificação ✅
- **Espaço vertical:** conteúdo preenche bem a área útil (kicker + heading + 2 painéis + nota) — sem void desproporcional ✅
- **Status: PASS**

### Slide 05 — Estratégia dos 2 minutos (T5 Light + steps)
- **Preview:** `slide-05-preview.jpg` (135 KB)
- **Paleta:** fundo off-white; 3 steps com borda magenta + badge circular magenta; anchor note rosa pale ✅
- **Lockup:** Variant A escura — ✅
- **Hierarquia:** kicker → heading com acento magenta → 3 passos numerados → nota âncora ✅
- **Tom:** imperativo gentil ("Escolha UMA tarefa", "Só faça.") — convite à micro-ação, consistente com pilar "micro-ações" do BRAND.md ✅
- **Insight anchor:** "O cérebro trava na partida — não no meio. O movimento cria o impulso." — salvável, compartilhável ✅
- **Status: PASS**

### Slide 06 — CTA Final (T5 + ícones)
- **Preview:** `slide-06-preview.jpg` (143 KB)
- **Paleta:** fundo off-white; heading magenta; callout glass; disclaimer rosa pale; ícones SVG magenta ✅
- **Lockup:** Variant A escura — ✅
- **CTA:** heading + body centrado + callout com DM e bio link + 3 ícones (curtir/salvar/compartilhar) — múltiplos vetores de ação ✅
- **Disclaimer:** presente e claro ("não substitui avaliação clínica") — obrigatório para conteúdo sobre TDAH/Burnout ✅
- **Ícones:** heart, bookmark, paper plane em magenta — mesmo padrão dos outros carrosséis do audit ✅
- **Status: PASS**

---

## Resumo Geral

**Resultado: 6/6 PASS** — nenhum warn ou fail remanescente.

**Correções aplicadas durante validação:**
- Slides 02 e 03: excesso de espaço em branco na base (warn após primeira passagem) → corrigidos com centralização vertical → pass na segunda passagem.

**Alinhamento com AUDIT.md:**
- Paleta magenta/off-white/preto coerente com evidências dos posts `p001`–`p009`
- Lockup Variant A presente em todos os slides (adequado para T5/Info Carousel)
- Tom PT-BR, segunda pessoa ("você"), acolhimento + educação + convite à micro-ação
- Faixas magenta rotacionadas presentes nos slides 01 e 03 (assinatura da marca)
- Zona segura inferior ≥ 276px respeitada em todos os slides

**Alinhamento com BRAND.md:**
- Pilares cobertos: "Regulação e TCC/DBT", "Micro-ações", "Padrões e narrativa"
- Público: jovens adultas em transição, especificamente profissionais com sensação de "cérebro travado"
- Disclaimer clínico presente (slide 06) — coerente com CRP/credencial da bio
- CTA: DM + link bio (bio.site/stephaniefalanque) — conversão principal do perfil

**Foto Unsplash:**  
"A woman rests her face in her hands" — Tsimur Asayonak / Unsplash License (free)  
Photo ID: `photo-1773496396339-447f78cc8fac`  
Salva como: `bg-burnout.jpg` (287 KB, 768×1376, crop center)

---

*Phase D completa. Carrossel pronto para revisão final.*  
*Export JPG (`--export --confirm`) requer aprovação explícita.*
