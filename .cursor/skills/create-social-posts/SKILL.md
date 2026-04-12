---
name: create-social-posts
description: >-
  Gates Instagram posts, carousels, and Stories on mandatory context before
  producing copy or slide HTML. Stops with numbered questions when intake is
  incomplete or vague; uses instagram-audits/, AUDIT.md, optional BRAND.md in
  the audit folder, and project rules in `.cursor/rules/social-media/`
  (instagram-feed, instagram-stories, image-designer) plus marketing rules. Use
  for posts, carousels, Stories, captions, legendas, conteúdo from text, or
  Instagram briefings. Triggers include "criar post", "carrossel", "stories",
  "legenda", "conteúdo a partir deste texto", "briefing". Full workflow (rules,
  Playwright pré-validação, UI/image prompts, glass panels, Unsplash, dense CTA
  layout, explicit JPG export consent) is in Phases A–E in SKILL.md.
---

# Context-gated marketing content (post + carrossel + Stories)

Orchestrate **Instagram post** (copy-first), **Instagram carousel** (repo: HTML/CSS under `instagram-audits/`), and **Instagram Stories** (copy-first, structured per frame; 9:16) workflows. **Do not** deliver final copy or slides until mandatory context is satisfied.

**Flow in this file:** Phase A (intake) → Phase B (context gate) → Phase C (execution: Post / Carousel / Stories per attached rules; carrossel subsections for prompts, HTML/CSS, `BRAND.md`, Unsplash, vertical centering, CTA denso) → Phase D (Playwright + `AUDIT.md` for repo carousels) → Phase E (export JPG só com sim explícito). Anti-patterns and defaults close the document.

For criterion nuance and examples, see [context-checklist.md](context-checklist.md).

---

## Phase A — Intake and classification (always first)

1. **Delivery type**
   - **Post**: caption, thread, multi-format ideas, etc. — copy-first.
   - **Carousel**: HTML/CSS in `instagram-audits/<date>-<handle>/carousels/<slug>/`, aligned with [.cursor/rules/marketing/marketing-carousel-growth-engine.md](../../rules/marketing/marketing-carousel-growth-engine.md).
   - **Stories**: sequência de 3–7 frames, 9:16, elementos interativos obrigatórios — copy-first com output estruturado por frame. Alinhado a [.cursor/rules/social-media/instagram-stories.md](../../rules/social-media/instagram-stories.md).

2. **Narrative format (when delivery is Carousel):** Do prompt, identificar qual dos sete formatos narrativos em [.cursor/rules/social-media/instagram-feed.md](../../rules/social-media/instagram-feed.md) se aplica: **Editorial**, **Listicle**, **Tutorial**, **Mito vs Realidade**, **Antes e Depois**, **Storytelling**, **Problema → Solução**. Se não estiver claro na Phase B, incluir como pergunta recomendada (ver gate).

3. **Extract from the prompt** anything already stated: theme, facts, audience, tone, CTA, language, profile/handle, legal/ethical constraints.

4. **Audit folder and `BRAND.md` (when path or handle is known)**  
   If the delivery ties to `instagram-audits/<data>-<handle>/`, assume there may be a sibling **`BRAND.md`** at the root of that folder (`instagram-audits/<data>-<handle>/BRAND.md`). You **do not** need the file to pass the gate; in **Phase C**, if that path is the working audit and **`BRAND.md` exists**, you **must** read it and fold it into planning (see below). If the path is not yet known, the gate still applies as usual. For **screenshot-based profile capture layout** (meta, grid, posts, reels folders), see [map-instagram-profile](../map-instagram-profile/SKILL.md).

---

## Phase B — Context gate (mandatory)

If **any required row** below is missing or **too vague** (see [context-checklist.md](context-checklist.md)): **STOP**. Do **not** write the post or build slides.

Instead respond with:

1. **Summary** of what you understood (1–3 sentences).
2. **Numbered list** of gaps, each with a direct question (or short options when helpful).
3. The line: _Quando você responder, continuo com a criação._

### Required criteria

| Criterion                                                                                             |     Post     |            Carousel            | Stories |
| ----------------------------------------------------------------------------------------------------- | :----------: | :----------------------------: | :-----: |
| Piece objective (educate, engage, convert, debunk, etc.)                                              |      ✓       |               ✓                |    ✓    |
| Target audience or niche (or explicit reference to the profile)                                       |      ✓       |               ✓                |    ✓    |
| Content substance: topic, key messages, myths/facts, data — not only “talk about anxiety”             |      ✓       |               ✓                |    ✓    |
| Language and tone (or “follow AUDIT.md / BRAND.md for profile X” when those files exist)                |      ✓       |               ✓                |    ✓    |
| Platform / format (e.g. IG caption, carousel N slides in repo)                                        |      ✓       | implicit if already “carousel” | implicit if already “Stories” |
| **Carousel:** profile (`instagram-audits/...`) or folder path + confirmation that `AUDIT.md` was read |      —       |               ✓                |    —    |
| **Narrative format** (7 opções em `instagram-feed.md`)                                                |      —       |          recomendado           |    —    |
| **Interactive element type** (poll / quiz / question box / emoji slider)                              |      —       |               —                |    ✓    |
| **Engagement goal** (retenção vs descoberta / alcance)                                                  |      —       |               —                |    ✓    |
| Restrictions (no over-promising; therapeutic disclaimer if sensitive)                                 | if sensitive |          if sensitive          | if sensitive |

### Optional (ask only if relevant)

CTA preference, hashtags, length, formality, campaign date. For **Carousel**, if the narrative arc is unclear, ask which of the seven formats in `instagram-feed.md` applies (Editorial, Listicle, Tutorial, Mito vs Realidade, Antes e Depois, Storytelling, Problema → Solução).

---

## Phase C — Execution (only after the gate passes)

Attach the appropriate rule(s) with `@` — **do not** paste long excerpts here:

- **Post e Carrossel — copy** (formatos narrativos do carrossel, 40–80 palavras por slide quando aplicável, formato de output canónico de legenda/feed): [.cursor/rules/social-media/instagram-feed.md](../../rules/social-media/instagram-feed.md)
- Post / strategy / multi-format: [.cursor/rules/marketing/marketing-content-creator.md](../../rules/marketing/marketing-content-creator.md)
- **Post — refinamento estético da legenda e, quando aplicável, direção visual** (ritmo, hierarquia de leitura, alinhado a `AUDIT.md` / `BRAND.md`): [.cursor/rules/design/design-ui-designer.md](../../rules/design/design-ui-designer.md)
- **Stories — copy e estrutura por frame:** [.cursor/rules/social-media/instagram-stories.md](../../rules/social-media/instagram-stories.md)
- **Stories e Carrossel — viewport, tipografia mínima, contraste, HTML self-contained, grid/flex:** [.cursor/rules/social-media/image-designer.md](../../rules/social-media/image-designer.md)
- Carousel build + validation + export policy: [.cursor/rules/marketing/marketing-carousel-growth-engine.md](../../rules/marketing/marketing-carousel-growth-engine.md)
- **Carousel `image_prompt` strings** (e.g. in `slide-prompts.json`): [.cursor/rules/design/design-image-prompt-engineer.md](../../rules/design/design-image-prompt-engineer.md)
- **Carousel `slides.css` + `slide-*.html`** under `instagram-audits/<data>-<handle>/carousels/<slug>/`: [.cursor/rules/social-media/image-designer.md](../../rules/social-media/image-designer.md) (requisitos técnicos de tipografia e canvas) + refinamento estético sistemático alinhado a [.cursor/rules/design/design-ui-designer.md](../../rules/design/design-ui-designer.md) — ver subsecção abaixo.

After context is sufficient, **follow the chosen rule end-to-end** (or both if the user wants briefing plus implementation).

### Post — refinamento estético (legenda / leitura)

Para entregas **Post** (copy-first), anexar **instagram-feed**, **UI Designer** junto de **marketing-content-creator**: aplicar ritmo, hierarquia de leitura e clareza na legenda; tom e identidade verbal em **`BRAND.md`** quando existir; evidência de estilo visual em **`AUDIT.md`** quando for relevante para sugestões de imagem, capa ou formato único. Para ficheiros **`image_prompt`** estruturados em JSON, manter a rule **Image Prompt Engineer**; o UI Designer cobre a camada editorial/leitura e direção visual geral sem duplicar esse fluxo.

### Stories — copy e estrutura de frames

Para entregas **Stories**, anexar [instagram-stories.md](../../rules/social-media/instagram-stories.md) e seguir o formato de output por frame (Visual / Text Overlay / Interactive Element / Sticker).

Regras obrigatórias:

- Sequência de **3–7 frames** com arco narrativo: Opener → Contexto → frame interativo → Fechamento/CTA.
- **Mínimo um** elemento interativo (poll, quiz, question box, emoji slider).
- Tom casual; **máximo 2–3 linhas** de texto por frame.
- **Sem** hashtags nem estrutura formal de legenda de feed.
- Viewport **1080×1920** (9:16). Tamanhos mínimos de tipo (de [image-designer.md](../../rules/social-media/image-designer.md)): Hero **56px**, Heading **42px**, Body **32px**, Caption **20px**.

### Carrossel — prompts de imagem (`slide-prompts.json`)

When creating or revising **`slide-prompts.json`**, alinhar o **copy** que vai para os slides a [.cursor/rules/social-media/instagram-feed.md](../../rules/social-media/instagram-feed.md) (40–80 palavras por slide salvo pedido explícito em contrário, hierarquia headline + apoio). Attach **Image Prompt Engineer** and apply its workflow to every **`image_prompt`**:

1. **Surface hero** — Treat each slide as a designed plane (layout, type, stickers, lockup), not a portrait scene unless the brief requires people.
2. **Layered stack** — Order: **subject** (zones, headline/body hierarchy, accents, brand placement) → **environment/surface** (paper, split blocks, texture) → **lighting** (soft, even light on the plane; no hotspots on type) → **technical** (9:16, safe zones, sharp legible type) → **style** (brand mood from `AUDIT.md` / `BRAND.md` / `visual_dna`) → **negatives** when the target tool supports them (illegible text, extra logos, random people, clutter).
3. **Copy fidelity** — Repeat **exact** on-slide strings and **language** (e.g. Portuguese) when the prompt describes typography; specify label vs headline vs body scale.
4. **Series coherence** — Keep palette, material language, and lockup rules consistent across slides; per-slide prompts should only change layout emphasis and copy, not random visual DNA.

Do not replace **`AUDIT.md`**-grounded facts with generic stock aesthetics; prompts must stay aligned to the audit folder’s visual identity.

### Carrossel — HTML/CSS (`slides.css`, `slide-XX.html`)

When implementing carousels under **`instagram-audits/<data>-<handle>/carousels/<slug>/`**, attach **[image-designer.md](../../rules/social-media/image-designer.md)** para requisitos técnicos e **UI Designer** para refinamento estético; tratar o slide como **fixed canvas** (tipicamente 768×1376 no repo), não como UI responsiva — mesma disciplina. **Tamanhos mínimos obrigatórios** (de `image-designer.md`): Hero **58px** · Heading **43px** · Body **34px** · Caption **24px**. Nenhum texto legível abaixo de **24px** no carrossel (piso absoluto **20px** em qualquer plataforma). **Font weight** mínimo **500** para body e acima. **Sem** contador de slides nas imagens (ex.: “1/6”) — o Instagram exibe navegação nativa. O UI Designer faz **sempre** uma passagem de **análise e refinamento estético** no conjunto de slides (coerência entre slides, ritmo visual, polish de tokens/tipo/espaço), **além** dos itens seguintes e **sem** contradizer `AUDIT.md` / `BRAND.md` em paleta ou lockup.

1. **Tokens in `:root`** — Centralize colors, spacing, radii, shadows, and semantic names (e.g. headline vs body vs accent); avoid one-off hex in individual slides when a token exists or should exist. **Documentar o design system** (tokens em `:root`) **antes** de fechar slides individuais — alinhado a `image-designer.md`.
2. **Typography system** — Define a clear scale (label / headline / body / CTA), line-height, and weight roles; keep hierarchy consistent across all `slide-*.html` files in the folder.
3. **Spacing rhythm** — Use a consistent base unit (e.g. 4px or 8px multiples) for padding, gaps, and margins so the set feels like one system.
4. **Contrast & legibility** — Aim for readable on-slide text (WCAG-minded contrast for body and headlines on colored or textured backgrounds); avoid low-contrast gray-on-gray for main messages unless the audit explicitly uses that as a deliberate device.
5. **Reuse** — Prefer shared classes in `slides.css` (layout regions, sticker/tape treatments, footers) over duplicating the same declarations in each HTML file.
6. **Caixas escuras (notas, CTAs, rodapés)** — **Não** usar blocos com fundo **preto** ou cinza **totalmente opaco** como padrão. Quando for preciso contraste sobre fundo colorido ou lavado, preferir um **layout mais leve**: fundo escuro **semi-transparente** (token em `:root`, ex. `rgb(… / 0.5–0.65)`), **`backdrop-filter`** (vidro fosco) na captura Playwright, **padding/margem laterais** para a caixa não encostar às bordas do slide, **border-radius** e sombra suave; manter texto legível (peso, tamanho, linhas divisórias em branco semitransparente se fizer sentido). Só usar painel sólido escuro se o **`AUDIT.md`** mostrar esse padrão de forma **explícita** no feed.

`AUDIT.md` (and previews) remain the authority for **brand-specific** colors and motifs; UI Designer rules **shape how** tokens, type, and spacing are structured, not override feed-evidenced palette choices.

### `BRAND.md` no audit (quando o ficheiro existir)

Quando o trabalho for para uma pasta `instagram-audits/<data>-<handle>/` e existir **`BRAND.md`** nessa raiz:

1. **Ler** `BRAND.md` **antes** de fechar o plano de post (ângulo, mensagens, CTA) ou de definir a narrativa / ordem / headlines dos slides do carrossel.
2. **Usar** o que o ficheiro definir como auxílio de planejamento: posicionamento, público, pilares editoriais, tom e voz, promessa, credenciais e disclaimers, mix editorial, pistas de estrutura de slides, tokens ou notas gráficas de marca que lá constem.
3. **Não substituir** `AUDIT.md`: o audit continua a fonte principal para **evidências do feed**, limitações da captura e **checagem de identidade visual** em Phase D. Se `BRAND.md` e `AUDIT.md` divergirem em detalhe visual, **prevalência na validação de layout/cores/lockup** é o **`AUDIT.md` + previews**; `BRAND.md` orienta sobretudo **conteúdo, tom e planejamento editorial**.

**Carrossel:** a implementação HTML/CSS em Phase C **não** encerra o fluxo sozinha — Phase D (pré-validação) é **obrigatória** antes de tratar o carrossel como pronto para revisão final ou export.

### Carrossel — Fotos de fundo humanizadoras (Unsplash)

**Quando faz sentido:** slides que já usam layout de fundo fotográfico (div `.photo-bg`, `.pink-wash` ou similar com overlay de gradiente) e cujo tema se beneficia de uma cena humana real — capas de temas sociais/relacionais, slides introspectivos, CTAs de conexão/DM. **Não aplicar** em slides de papel com texto denso (o ruído visual prejudica a legibilidade).

**Fluxo obrigatório (4 passos):**

1. **Buscar no Unsplash** — usar web search com query específica, ex.: `unsplash photo [descrição da cena] site:unsplash.com`. Escolher fotos alinhadas ao tema do slide e à paleta do audit (warm tones, poses naturais, sem fundo genérico de stock). Verificar que a foto é **gratuita** (Unsplash License, não Unsplash+).

2. **Obter o URL CDN** — fazer fetch da página da foto (`https://unsplash.com/photos/<slug>`) e extrair o `src` da imagem no formato `https://images.unsplash.com/photo-XXXXXXXXXX?...`. Construir o URL de download com dimensões do slide: `?w=768&h=1376&fit=crop&q=80&auto=format`.

3. **Baixar localmente com curl** — **nunca** usar URL externo diretamente no CSS: o Playwright não carrega imagens remotas de forma confiável durante o render. Salvar na pasta do carrossel com nome descritivo:
   ```bash
   curl -sL "https://images.unsplash.com/photo-XXXX?w=768&h=1376&fit=crop&q=80&auto=format" \
     -o instagram-audits/<date>-<handle>/carousels/<slug>/bg-<descritor>.jpg
   ```

4. **Referenciar no CSS com caminho relativo e classe modificadora** — não usar inline style nem alterar a classe base. Criar uma classe modificadora em `slides.css` que sobrepõe apenas `background`, com o gradiente de overlay **na frente** e a foto **atrás**:
   ```css
   /* Photo: [descrição] — [Fotógrafo] / Unsplash */
   .photo-bg--<descritor> {
     background:
       linear-gradient(/* overlay de marca, mesmas opacidades do padrão do audit */),
       url("bg-<descritor>.jpg") center / cover no-repeat;
   }
   ```
   Aplicar a classe modificadora no HTML junto à classe base: `class="photo-bg photo-bg--<descritor>"`.

**Regras técnicas:**
- O pseudo-elemento `::after` da classe base (noise texture) continua aplicado automaticamente — não duplicar.
- Overlay com opacidade suficiente para manter contraste do texto (tipicamente 22–75% dependendo do slide).
- Registar fotógrafo e ID da foto como comentário no CSS e no `validation-report.md`.
- Verificar nos previews que a foto é visível através do overlay — se estiver completamente coberta, reduzir opacidade do gradiente ou ajustar `background-position`.

### Carrossel — Centralização quando há muito espaço em branco

**Quando aplicar:** se o miolo do slide (texto, faixas, blocos) ocupar **pouca altura** em relação ao canvas **9:16** (768×1376), deixando faixas vazias grandes acima e abaixo — **não** deixar tudo colado ao topo com `top: Npx` fixo como único eixo.

**O que fazer**

1. **Área útil** — Entre o **lockup de marca** (barra @handle + função) no topo e a **zona segura inferior** (~**276–300px** do fundo do slide, onde entram UI do Instagram + numeração opcional), tratar essa faixa como “corpo” do slide.
2. **Eixo vertical** — No corpo, usar um contentor (ex.: flex column com `justify-content: center`, ou equivalente) para **centralizar o bloco principal** no eixo vertical. Slides de capa ou faixas centradas podem também usar alinhamento horizontal ao centro quando fizer sentido (`align-items: center` / `text-align: center`).
3. **Rodapé fixo** — Se o slide tiver **CTA ou barra escura ancorada em baixo**, centralizar só o bloco **acima** dessa barra (reservar altura explícita para o rodapé, para não sobrepor nem “esmagar” o miolo).
4. **Reutilizar padrão** — Preferir classes partilhadas em `slides.css` (ex.: contentor “faixa central” reutilizável) em vez de duplicar `top: 50%` + `translateY` por slide, para manter consistência entre carrosséis do mesmo audit.

**Phase D:** nos previews, verificar se algum slide com pouco texto ainda parece “vazio em baixo” por excesso de alinhamento ao topo; se sim, **corrigir** HTML/CSS e repetir `--validate`.

### Carrossel — Slide CTA final (ou bloco denso): espaçamento **quando necessário**

**Quando aplicar:** no preview, o último slide (ou qualquer slide com **vários pedidos** — DM, comentário numerado, bio, salvar —) parece **apertado**: parágrafo único longo dentro do vidro, legendas 1–4 dentro da mesma caixa, margens internas fracas, pouco espaço entre faixas de título e o rodapé.

**Não** é obrigatório em todo carrossel: slides CTA **curtos** ou com **um único foco** podem manter o padrão simples já usado no projeto. Usar o padrão abaixo **só quando** a densidade ou o feedback do utilizador o exigir.

**Padrão recomendado (replicar em `slides.css` do carrossel com classes partilhadas)**

1. **Legenda numerada fora do vidro** — Colocar o mapa **1 · … · 2 · …** (e variantes) **no fundo do slide** (ex.: lavado rosa/papel), **acima** do painel em vidro, tipografia legível e números em destaque (token de acento). O vidro fica para **mensagem principal + 1–2 linhas de apoio**, não para listar os quatro temas entre parênteses.
2. **Coluna no rodapé** — Contentor do fecho (ex.: `slide-footer-cta` + modificador tipo `--column`) em **flex column** com **gap generoso** (ordem de **40–56px**) entre legenda e vidro, para o olho “respirar” entre blocos.
3. **Vidro centrado e com teto de largura** — Painel CTA com **`max-width`** (~620–640px) e **`margin-left` / `margin-right` auto** dentro da área já paddingada do slide, **padding interno** confortável (ex.: ~44–50px vertical/lateral), **margens** claras entre título (DM), corpo e linha “salvar”.
4. **Copy enxuta no vidro** — Preferir **frases curtas** e hierarquia (título forte + instrução numa linha + bio numa linha + salvar com separador). Se ainda apertar, **encurtar texto** antes de reduzir legibilidade (tamanho mínimo abusivo).
5. **Reserva vertical do miolo** — Se as faixas magnéticas de pergunta competem com o rodapé, **subir** o bloco central (ex.: aumentar `bottom` do contentor do miolo em relação ao padrão, como `slide__body-centered--cta-final-mid`) para abrir faixa entre pergunta, legenda e CTA — sempre **acima** da zona segura inferior. **Atenção ao glass:** o painel de vidro estende-se para cima a partir do seu `bottom` anchor conforme a altura do seu conteúdo interno (padding + linhas de texto). O `bottom` do contentor do miolo deve ser maior do que o topo real do glass, não apenas maior do que o `bottom` do glass — verificar nos previews se o glass cobre qualquer linha de texto ou legenda do miolo; se sim, aumentar o `bottom` do contentor central até haver folga visível (tipicamente 80–120px acima do topo do glass).
6. **Faixas (`.strip--cta`) sem “colar”** — Garantir **padding interno** confortável nas faixas (vertical e horizontal), **`gap` maior** entre faixas empilhadas (ex.: 22–28px), **`line-height`** explícito se o texto encostar às bordas, e **`padding-bottom`** no grupo de faixas (ex.: classe tipo `cta-upper--strips-spaced`) para separar do texto/legenda abaixo; no preview, se as faixas ainda roçam o bloco seguinte, subir o miolo ou aumentar padding da legenda numérica.
7. **Sobreposição faixas × texto (transform)** — Se faixas com **`transform`/`box-shadow`** pintarem **por cima** de legenda ou corpo (duas zonas **absolute** diferentes), **não** confiar só em `padding` no fluxo antigo: colocar faixas + texto seguinte no **mesmo** contentor **flex column** com **`gap`** real (padrão `slide--final-cta` + `.final-cta-mid` no exemplo do repo), rotação mais suave no miolo se preciso, e vidro/CTA pesado num **rodapé** separado com `z-index` coerente.
8. **Referência no repo** — Implementação de exemplo: `instagram-audits/2026-04-07-stephaniefalanque/carousels/vida-social-relacionamentos/slide-06.html` e classes associadas no `slides.css` dessa pasta (ajustar tokens/nomes se outro audit exigir, mantendo a **lógica**).

**Phase D:** ao rever previews, se o slide final CTA estiver **denso** ou **ilegível à primeira leitura**, aplicar este padrão (ou equivalente alinhado ao UI Designer) e voltar a correr `--validate`.

---

## Phase D — Pré-validação (Playwright + identidade visual do audit)

**Aplica-se só a carrossel** no repo, **depois** de existirem `slide-01.html` … `slide-06.html` (ou o conjunto acordado), `slides.css` e ficheiros auxiliares previstos na regra do carrossel.

### O que fazer

1. **Confirmar a pasta de audit correta** — o carrossel vive em `instagram-audits/<data>-<handle>/carousels/<slug>/`; o ficheiro de verdade para identidade visual é o **`AUDIT.md` do ascendente** `instagram-audits/<data>-<handle>/AUDIT.md` (mesmo handle/data da pasta do utilizador). **Não** substituir por outro audit nem por memória de um perfil genérico. Se existir **`BRAND.md`** nessa mesma pasta ascendente, usar também na revisão dos previews para **tom, pilares, mensagens e coerência editorial** (CTA, linguagem, promessa), sem contradizer o que `AUDIT.md` + previews impõem em layout e marca gráfica.
2. **Gerar capturas com Playwright** — a partir da raiz do repo:  
   `node scripts/export-slides.js --validate <caminho-da-pasta-do-carrossel>`  
   Isto abre cada HTML no Chromium, viewport **768×1376**, e grava **`slide-XX-preview.jpg`**. Este passo é a **pré-validação técnica** (render + screenshot); o script **não** julga sozinho se a marca está correta.
3. **Avaliar identidade visual contra o `AUDIT.md` lido** — inspecionar cada preview e comparar de forma explícita com o audit da pasta certa. Derivar um checklist curto do próprio ficheiro (ex.: paleta, lockup @handle + linha de função, zona segura inferior ~20%, estilo colagem/stickers/texturas se constarem no audit, tom visual “terapia acessível” vs. clínico frio). Incluir **uso do espaço vertical**: em slides com pouco conteúdo, o miolo deve estar **razoavelmente centrado** na área útil (ver subsecção _Centralização quando há muito espaço em branco_ em Phase C), salvo quando um rodapé fixo exige reserva explícita em baixo. Em **slides CTA finais com múltiplos pedidos**, verificar se o layout está **apertado**; se sim, seguir a subsecção _Slide CTA final (ou bloco denso): espaçamento quando necessário_ em Phase C. Incluir **legibilidade e hierarquia** (contraste texto/fundo, escala label/headline/corpo) como revisão complementar à subsecção _HTML/CSS_ da Phase C (disciplina UI Designer), sem contradizer o look evidenciado no feed. Anotar **pass** / **warn** / **fail** por slide quando relevante.
4. **Revisão obrigatória de usabilidade, legibilidade e estética (pós-previews)** — o script Playwright **só** gera imagens; **não** valida se o post “está bonito” ou legível em todas as zonas. Após o passo 2, rever **cada** `slide-XX-preview.jpg` com foco explícito em:
   - **Texto sobre foto ou lavado variável** — trechos fora do vidro (ex.: mapa “1 · … · 2 · …” acima do glass no CTA final) não podem usar a mesma cor de corpo pensada para **papel** (`--dark`, `--gray`) se o fundo tiver áreas escuras **ou claras** (pele, céu, janela); aplicar cor clara + `text-shadow`, **painel vidro / scrim** só atrás desse bloco, ou mover o texto para zona estável do layout.
   - **Contraste à primeira leitura** — especialmente números vs. descrição, bullets sobre gradiente, e notas em `note-box` sobre imagem; cruzar com a intenção WCAG da checklist técnica abaixo (4.5:1 quando mensurável).
   - **Estética e coerência** — ritmo entre faixas, vidro e rodapé; nada cortado pela zona segura; paleta alinhada ao audit sem “manchas” acidentais.
   Se algo falhar nesta revisão: **corrigir CSS/HTML**, repetir `--validate`, atualizar `validation-report.md` com nota na coluna do slide (ex.: “warn → pass após `.cta-outside-key--on-photo`”).
5. **Se houver falha clara de identidade ou de layout** (texto essencial na zona inferior coberta pelo IG, lockup em sítio errado, paleta destoante do audit, ausência de elementos de marca exigidos pelo audit, **ou miolo colado ao topo com excesso de vazio inferior em slide pouco denso**): **corrigir HTML/CSS** e **repetir** o passo 2 até os previews estarem alinhados ou os warns ficarem apenas aceitáveis documentados.
6. **Registar** o resultado em **`validation-report.md`** na pasta do carrossel (resumo + por slide), amarrando critérios a secções ou temas do `AUDIT.md` da pasta correta (e, se existir, temas de **`BRAND.md`** relevantes a tom/pilares) — alinhado a [.cursor/rules/marketing/marketing-carousel-growth-engine.md](../../rules/marketing/marketing-carousel-growth-engine.md).

### Checklist técnico (`image-designer.md`)

Na revisão de cada preview, cruzar com [image-designer.md](../../rules/social-media/image-designer.md) e anotar **pass** / **warn** / **fail** quando aplicável:

- [ ] **Fontes:** carrossel — Hero ≥58px, Heading ≥43px, Body ≥34px, Caption ≥24px; Stories (se houver preview/HTML 9:16) — 56 / 42 / 32 / 20px.
- [ ] **Piso:** nenhum texto legível abaixo de **20px** em qualquer plataforma.
- [ ] **Peso:** font weight ≥**500** para body e níveis acima.
- [ ] **Contraste WCAG AA:** mínimo **4.5:1** texto/fundo.
- [ ] **HTML:** self-contained no espírito da rule — sem CDN externo além de **Google Fonts** `@import` (o repo pode usar `slides.css` partilhado no carrossel; não introduzir outros recursos remotos desnecessários).
- [ ] **Body / canvas:** dimensões exatas do viewport acordado (ex. 768×1376 no script do repo), sem margem indesejada, sem overflow de conteúdo essencial.
- [ ] **Layout:** CSS Grid ou Flexbox; `position: absolute` só para decoração, não para o fluxo principal de leitura.
- [ ] **Sem contador de slide** nas imagens (ex. “1/6”) — o Instagram exibe navegação nativa.
- [ ] **Design system** documentado (tokens em `:root`) antes de tratar o conjunto de slides como fechado.

### O que não é esta fase

- **Não** confundir pré-validação com **export final** (`slide-XX.jpg`): isso é Phase E e continua a exigir confirmação explícita do utilizador.
- **Não** tratar “corri o script e gerou JPG” como revisão: sem cruzar previews com o **`AUDIT.md` da pasta de audit correta** (e, quando existir, alinhar narrativa/tom ao **`BRAND.md`** desse audit), a Phase D **não** está cumprida.

---

## Phase E — Carousel close: JPG export (explicit user step only)

These rules **override** any looser reading elsewhere:

- **Forbidden** as part of an automatic “done” flow: `node scripts/export-slides.js --export --confirm` (or any final `slide-XX.jpg` export) without the user having answered **yes** in chat **after** you ask.
- **Allowed** without extra confirmation: HTML/CSS, `slide-prompts.json`, `caption.txt`, `validation-report.md`, and **`--validate`** only (previews `slide-XX-preview.jpg`).
- When Phase D is done and (if applicable) the user reviewed: **stop** and ask explicitly, same spirit as the carousel rule — e.g. _Deseja exportar os slides em JPG?_ Only if the user answers **affirmatively**, run `--export --confirm`.
- Phrases like “carrossel completo” or “finalizar” mean **code + Phase D pré-validação + `validation-report.md`**, **not** authorization to export final JPGs. The export question remains **mandatory**.

---

## Anti-patterns

- Do not invent profile, folder, or clinical facts without user-provided basis.
- When `instagram-audits/<data>-<handle>/BRAND.md` **exists**, do not skip it for post or carousel **planning**; still treat **`AUDIT.md`** as the anchor for feed-grounded visual validation in Phase D.
- Do not skip the gate by “assuming the obvious” for health/therapy topics.
- **Do not** skip Phase D for repo carousels: no “entregue” de carrossel sem `--validate` e comparação explícita dos previews ao **`AUDIT.md` da pasta `instagram-audits/<data>-<handle>/` correta**.
- **Never** export final slides without explicit post-gate user approval; do not treat generic “complete” / “finalize” as “yes” to `--export --confirm`.
- **Carrossel:** não deixar slides com pouco texto **só** ancorados ao topo se o preview mostrar **faixa vazia desproporcional** em baixo — aplicar centralização na área útil (Phase C) e validar em Phase D.
- **Carrossel:** não entregar `image_prompt` genéricos ou numa só frase vaga — aplicar o framework do **Image Prompt Engineer** (camadas, superfície, zonas seguras, negativos quando aplicável).
- **Carrossel:** não espalhar estilos ad hoc por `slide-*.html` sem tokens/escala — alinhar **`slides.css`** e HTML ao **UI Designer** e aos mínimos de **[image-designer.md](../../rules/social-media/image-designer.md)** (tokens, hierarquia tipográfica, ritmo de espaçamento).
- **Stories:** não entregar Stories **sem** elemento interativo — é o mecanismo primário de engajamento do formato.
- **Stories:** não reutilizar frame de carrossel como Story sem acrescentar contexto, interação ou valor novo.
- **Post / legenda:** não incluir **URLs clicáveis** no corpo da legenda — o Instagram não as suporta; usar link na bio ou **link sticker** em Stories.
- **Carrossel (copy / slide):** não criar slides com **menos de 40 palavras** (headline + texto de apoio combinados) sem pedido explícito do utilizador — slides superficiais não entregam valor de save (ver `instagram-feed.md`).
- **Design:** não usar font size abaixo dos **mínimos de plataforma** — hero **58px** no carrossel; **20px** como piso absoluto para qualquer texto legível.
- **Design:** não iniciar criação de slides **sem** documentar o design system (cores, fontes, espaçamento) primeiro.
- **Carrossel:** não usar caixas de texto, notas ou CTA com **fundo preto ou cinza chapado** por defeito — usar **opacidade + vidro** (e respiro lateral), exceto quando o **`AUDIT.md`** evidenciar blocos sólidos no feed.
- **Carrossel:** não empilhar **legenda longa + DM + bio + salvar** num **único parágrafo** dentro do vidro quando o preview mostrar densidade excessiva — aplicar o padrão _CTA denso_ em Phase C (legenda fora, coluna com gap, vidro centrado com max-width, copy curta).
- **Carrossel:** **legenda numerada ou corpo fora do vidro** sobre **foto** ou **lavado escuro** com a mesma cor que no papel (`--dark`, `--gray`) — em previews, isso costuma falhar em **usabilidade** (passo 4 da Phase D); usar texto claro + `text-shadow`, modifier dedicado, ou fundo semitransparente local.
- **Carrossel:** não assumir que o gap entre o `bottom` do contentor central e o `bottom` do glass é suficiente só pelo valor numérico — o glass cresce para cima conforme o seu conteúdo interno; **medir visualmente** no preview se o topo do glass sobrepõe algum texto do miolo (faixas ou legenda numerada) e, se sim, **aumentar o `bottom` do contentor central** até a sobreposição desaparecer.
- **Carrossel:** o contador de paginação (`.slide-num`, ex. `01 / 06`) deve ter `bottom` **menor** do que o `bottom` do glass — se os dois valores forem próximos ou iguais, o counter fica colado ou sobreposto à borda inferior do painel; garantir folga visível de ao menos ~60–80 px abaixo do glass (ex.: glass em `300px` → counter em `220px` ou menos).
- **Carrossel — fotos Unsplash:** não usar URL externo (`images.unsplash.com/...`) diretamente no CSS — o Playwright não carrega imagens remotas de forma confiável durante o render (slide pode parecer sem foto mesmo com CSS correto). **Sempre baixar com `curl` e usar caminho relativo** (`bg-<descritor>.jpg`). Validar nos tamanhos dos preview JPGs: slides com foto real serão significativamente maiores (ex.: >150 KB vs ~70–100 KB para fundo gradiente puro).

---

## Technical default vs final assets

- **Default technical completion** for carousels: Phase D complete (`--validate` run, previews checked against the **correct** parent `AUDIT.md`, `validation-report.md` written).
- **Final JPGs**: only after explicit user confirmation following Phase E.
