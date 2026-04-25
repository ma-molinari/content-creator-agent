# Diretrizes de UI — layout, marca e tokens

Documento único para o **front-end**, unificando o que estava em `docs/layout.md` e `docs/brand.md`. Cobre **estrutura de ecrã e padrões de produto** (papéis UI Designer / UX Architect) e **identidade, tokens e consistência visual** (Brand Guardian). Derivado das imagens em `docs/ui/`. Valores de cor são **inferência visual** até validação com conta-gotas no design final.

---

## Imagens de referência

| Arquivo | Produto na arte | Foco de UI / estrutura | Marca / tokens |
|--------|-------------------|------------------------|----------------|
| `docs/ui/version_1.png` | Talk Data to Me | Empty state centrado, chips de prompt, sidebar com estado ativo | Azul de estado ativo na rail, empty state, pouca sombra |
| `docs/ui/version_2.png` | Maskara.ai | Thread, cards de ficheiro, preview rico (ex.: LinkedIn), composer | CTA preto, gradientes em preview, sombra suave em card |
| `docs/ui/version_3.png` | Aplot AI | Sidebar expandida (busca, histórico, CTA), top bar, feature cards, glass/soft | Azul primário tipo produto, pastel em feature cards, glass/soft shadow |
| `docs/ui/auth_1.png` | CoLabs | Auth em coluna dupla: formulário + painel marketing | Azul saturado em CTA/links, logo em pill, split escuro/claro |

---

## Princípios transversais (das referências)

- **Sans-serif neutra** de produto (referência de família: Inter, Geist, SF Pro, system-ui) — alta legibilidade em chat e formulários.
- **Espaço em branco generoso** e hierarquia por peso (semibold/bold em títulos) e cor (texto primário vs. secundário).
- **Cantos arredondados** em escala (chips pill, inputs e cartões 8–24px, painéis hero 24–40px).
- **Profundidade:** alternância entre UI quase flat (`version_1`, formulário em `auth_1`) e **elevação leve** em cards e composer (`version_2`, `version_3`).

---

## Layout e padrões de UI

### Visão geral do padrão de produto

As quatro referências convergem em um **aplicativo de conversa com IA** em estilo SaaS:

- **Coluna esquerda fixa** (rail ou sidebar) para navegação global e, em variantes mais ricas, busca e histórico.
- **Área principal** com thread de chat ou **empty state** centrado (persona, título, atalhos).
- **Composer** na base (fixo ou “sticky”), largo, cantos arredondados, com anexos e ações secundárias (enviar, voz, modos).
- **Auth** em tela cheia com **split** formulário claro × marketing visual escuro (quando aplicável).

### Shell global (sidebar + main)

- **Rail estreita** (`version_1`, `version_2`): fundo cinza muito claro, separação sutil da área principal (borda ou contraste leve). Main em branco ou off-white.
- **Sidebar rica** (`version_3`): logo + busca em pill, lista de navegação (Home, Explore, Library…), seção **History** (“Today” com itens truncados), card **Upgrade** no rodapé.
- **Main**: conteúdo do chat com coluna de leitura implícita; empty state centralizado (`version_1`, `version_3`); em conversa, fluxo vertical com possível `max-width` central para legibilidade (`version_2`).

**Implementação sugerida:** `display: flex` — sidebar `flex: 0 0 [largura]`; main `flex: 1` e `min-width: 0` para overflow e scroll da thread.

### Navegação e icon rail

- **Agrupamento vertical:** topo (marca / menu), meio (ações primárias), base (configurações, créditos, avatar).
- **Estado ativo:** fundo preenchido em squircle ou retângulo arredondado (azul em `version_1`; cinza claro em `version_2` / `version_3` conforme a arte).
- **Inativos:** ícones em linha, cor neutra; alguns controles com borda leve (`+` em `version_1`).
- **Variante “produto completo”** (`version_3`): ícone de grade para menu expandido; item de lista com ícone + label (não só ícones).

Regra de produto: **um contexto ativo** por vez na rail (ex.: Home vs. Library).

### Área de chat

#### Empty state

- Avatar ou ícone de persona grande, título e subtítulo (`version_1`: “Talk Data to Me” + instrução para escolher prompt).
- Bloco **“Ask about:”** com **chips** (pills) e link para biblioteca de prompts (`version_1`).
- **Hero alternativo** (`version_3`): ícone com glow, headline “How Can I Assist You Today?”, fileira de **feature cards** (capabilities em grid horizontal).

#### Conversa

- **Cabeçalho** com nome do produto e chevron (`version_2`) — candidato a seletor de workspace/modelo.
- **Usuário:** mensagens à direita, bolhas em cinza claro (`version_2`).
- **Assistente:** à esquerda; texto mais “plano” ou com anexos como **cards de arquivo** (ícone por tipo, nome).
- **Conteúdo rico:** container externo com gradiente suave; card branco interno; CTAs na base alinhados à direita (`version_2`, preview estilo rede social).

#### Top bar (variante densa)

`version_3`: seletor de modelo, **New Chat** (botão escuro), **Export Chat**, avatar — útil como padrão quando o escopo incluir export e troca de modelo sem esconder tudo no header do chat.

### Composer / barra de entrada

Padrões observados:

| Elemento | Onde aparece |
|----------|----------------|
| Placeholder com ícone (varinha / texto) | `version_1` |
| Paperclip (anexo) | `version_1`, `version_2` |
| Contador de caracteres | `version_1` (0/1000) |
| Send circular | `version_1` |
| Mic / headphones | `version_2` |
| Modos (Reasoning, Create Image, Deep Research) | `version_3` |
| Container grande com sombra suave | `version_3` |

**Recomendação de componente:** `ComposerBar` com slots para prefixo (anexo), campo, sufixo (modos, voz, enviar) para cobrir todas as variantes sem fork de layout.

### Auth e marketing split (`auth_1`)

- **Coluna esquerda:** logo em pill, “Welcome Back!”, labels acima dos campos, inputs com fundo cinza claro, toggle Remember me, link Forgot password, CTA primário full-width, OAuth (Google), rodapé com Sign up.
- **Coluna direita:** painel escuro com ilustração 3D, headline + parágrafo, **dots de carrossel** na base; cantos muito arredondados no painel.

**Desktop:** grid ou flex 1fr 1fr. **Mobile:** empilhar colunas; painel marketing recolhível, oculto ou em segundo passo.

### Grid, flex e breakpoints

- **Thread:** coluna flex; `align-self: end` para usuário, `start` para assistente.
- **Chat central:** `max-width` + `margin-inline: auto` para linha de leitura confortável.
- **Feature cards** (`version_3`): grid horizontal com wrap em telas menores.
- **Breakpoints:** colapsar rail para **drawer** ou **bottom nav**; reduzir padding; chips em wrap; cards ricos com scroll interno se necessário.

### Inventário de componentes (nomes sugeridos)

**Shell:** `AppShell`, `SidebarRail`, `SidebarExpanded` (variante com busca/histórico), `NavItem`, `NavIcon`, `BrandMark`, `UserMenuAvatar`.

**Chat:** `ChatLayout`, `ChatHeader`, `ChatThread`, `ScrollArea`, `EmptyChatState`, `PersonaHero`, `PromptChip`, `PromptLibraryLink`, `MessageBubbleUser`, `MessageAssistant`, `AttachmentFileCard`, `RichPreviewCard` (gradiente + inner card + ações).

**Composer:** `ComposerBar`, `ComposerTextField`, `ComposerToolbar`, `AttachmentButton`, `SendButton`, `CharacterCounter`, `VoiceButton`, `ModeChip` (Reasoning, etc.).

**Produto denso:** `TopActionBar`, `ModelSelector`, `FeatureCard`, `HistorySection`, `SearchField`, `UpgradeCard`.

**Auth:** `AuthSplitLayout`, `AuthFormColumn`, `MarketingPanel`, `LabeledInput`, `PasswordInput`, `RememberMeToggle`, `PrimaryButton`, `OAuthButton`, `CarouselDots`.

### UX Architect: IA, tema e foco

- **Informação:** rail = navegação global persistente; main = contexto da conversa; empty state = onboarding + atalhos; header com nome do produto pode agrupar troca de workspace/modelo.
- **Tema:** as referências são majoritariamente **light**. O padrão do repositório recomenda suporte a **light / dark / system**; posicionar toggle em **Settings** na rail ou no menu de usuário quando não houver padrão visível nas capturas.
- **Ordem de foco (app chat):** itens da rail (topo → meio → base) → chips ou primeiro focável do empty state → composer (anexo → campo → ações à direita). Em thread: região principal scrollável antes do composer fixo; após enviar, manter foco lógico no campo ou no último assistente.
- **Acessibilidade:** anunciar item ativo na rail; landmarks para thread e composer; contraste e alvo de toque ≥ 44px onde possível; suporte a `prefers-reduced-motion` para animações de cards e glow.

### Handoff para implementação

1. Fundação: variáveis CSS (secção **Token set unificado** abaixo) + layout flex/grid.
2. Shell + uma variante de sidebar (mínima vs. expandida).
3. Empty state + thread + composer com composição por slots.
4. Auth split como rota isolada.
5. Estados de carregamento, erro e vazio alinhados à hierarquia visual das referências.

**Última revisão (layout):** 2026-04-10 — baseado em `docs/ui/*.png` e síntese de revisão UI/UX.

---

## Marca e design tokens

### Papéis de cor (semântica)

- **Fundo app (camada 0):** branco `#FFFFFF` ou off-white `#F8FAFC` / `#F9FAFB` (variantes entre refs).
- **Superfície levantada:** sidebar, inputs e composer — `#F7F7F7`–`#F9FAFB` ou branco com borda sutil.
- **Texto primário:** preto/carvão `#000000`–`#1E293B`.
- **Texto secundário:** `#666666`–`#64748B`.
- **Bordas / divisores:** `#E0E0E0`–`#E5E7EB`.
- **Ação primária da marca:** família de **azul** (ver conflitos abaixo) ou **preto** para ênfase máxima de ação (`version_2`).
- **Acentos de plataforma:** LinkedIn, tipos de arquivo etc. — sempre tokens `accent-platform-*`, nunca como cor primária da aplicação.

### Tabela de aproximações (validar no design)

| Papel sugerido | version_1 | version_2 | version_3 | auth_1 |
|----------------|-----------|-----------|-----------|--------|
| Fundo principal | `#FFFFFF` | ~`#F9FAFB` | ~`#F8FAFC` | `#FFFFFF` (form) |
| Sidebar / superfície | ~`#F7F7F7` | cinza claro | `#FFFFFF` / cinza muito claro | — |
| Estado ativo (nav) | ~`#5072B1`–`#5E7BB5` | cinza em ícone ativo | ~`#F1F5F9` highlight | — |
| CTA / link forte | (sidebar) | `#000000` botão | ~`#2563EB` | ~`#3B4FFE`–`#4353FF` |
| Texto primário | `#000000` | ~`#111827` | ~`#1E293B` | `#000000` |
| Texto secundário | ~`#666666` | ~`#6B7280` | ~`#64748B` | labels ~`#333333` |

### Pastéis e feature cards (`version_3`)

Uso decorativo para capacidades (ícones em cápsulas coloridas), não como cor única de marca:

- Verde: fundo ~`#F0FDF4`, ícone ~`#22C55E`
- Azul: ~`#EFF6FF` / ~`#3B82F6`
- Roxo: ~`#FAF5FF` / ~`#A855F7`
- Laranja: ~`#FFF7ED` / ~`#F97316`

### Tipografia

- **Família:** uma stack sans moderna; fallback: `system-ui, "Segoe UI", Roboto, sans-serif`.
- **Pesos:** regular (corpo, chat), medium (labels de UI), semibold/bold (títulos, marca).
- **Escala indicativa (px):** 12 (meta, datas), 14–16 (corpo, inputs), 20–24 (títulos de área), 28–40 (hero marketing / welcome).
- **Empty state** costuma ser centralizado; **thread** alinhada à esquerda — variante de layout, não necessariamente escala tipográfica diferente.

### Raios (border-radius)

Sistema em múltiplos de **4px** sugere consistência com as refs:

| Token sugerido | Uso |
|----------------|-----|
| `radius-sm` 6px | Pequenos controles, alguns botões secundários |
| `radius-md` 8–12px | Inputs, botões, ícones em squircle |
| `radius-lg` 12–16px | Cards, composer, células de arquivo |
| `radius-xl` 16–24px | Containers grandes, modais |
| `radius-2xl` 24–40px | Painel marketing (`auth_1`), shells “card” |
| `radius-full` | Chips, pills, busca, toggles |

### Sombras e elevação

- **Flat:** hierarquia por cor de fundo e borda (`version_1`, formulário `auth_1`).
- **Card flutuante:** sombra difusa baixa opacidade (`version_2` preview social).
- **Soft UI / glass:** `0 10px 15px -3px rgba(0,0,0,0.05)` ou similar (`version_3` — input e cards).

**Diretriz:** reservar sombra a **cards de resultado**, **composer** e **dropdowns**; manter inputs simples sem sombra ou com sombra mínima no foco.

### Espaçamento

- **Grid base:** 4px ou 8px (gaps de chips, espaçamento entre label e campo).
- **Padding interno:** ~16–20px em inputs; ~24px+ em cards largos.
- **Seções verticais:** 24–32px entre blocos principais no empty state e no formulário de auth.

### Logo e tratamento de marca

- **Persona/avatar** como âncora emocional (`version_1`).
- **Ícone + wordmark** na sidebar e header (`version_2`, `version_3`).
- **Símbolo geométrico + wordmark em pill** (`auth_1`).

Para **content-creator-agent:** documentar **logomark mínimo**, **logotype**, **clear space** e uso opcional de **avatar do agente** sem substituir o logo na navegação principal.

### Voz e tom (trechos das artes)

- **Talk Data to Me:** cordial, personificado (“Steven”), instrutivo.
- **Maskara.ai:** objetivo, focado em tarefa e status.
- **Aplot AI:** acolhedor, capacidade (“How Can I Assist You Today?”), upgrade como upsell claro.
- **CoLabs:** acolhimento (“Welcome Back!”) + aspiracional no painel (“Harness Collective Potential.”).

Uniformizar tom de **microcopy** na aplicação alvo conforme posicionamento do produto (ver PRD/spec).

### Conflitos entre referências e resolução

1. **CTA primário:** azul de nav (`version_1`) vs **preto** (`version_2`) vs **azul saturado** (`auth_1`).
2. **Fundo:** branco puro vs off-white frio.
3. **Três famílias de azul** distintas se misturadas sem papéis.
4. **Elevação:** flat vs sombra em card/composer.
5. **Densidade de sidebar:** só ícones vs lista + histórico + CTA.

### Token set unificado recomendado — content-creator-agent

Objetivo: uma base implementável em CSS variables / design tokens, alinhada ao Guardian e às quatro imagens.

```css
:root {
  /* Neutros */
  --color-bg-app: #f9fafb;
  --color-bg-surface: #ffffff;
  --color-bg-muted: #f3f4f6;
  --color-border-subtle: #e5e7eb;
  --color-text-primary: #111827;
  --color-text-secondary: #6b7280;
  --color-text-muted: #9ca3af;

  /* Marca — escolher um azul master após validação (ex.: #2563eb) */
  --color-brand-primary: #2563eb;
  --color-brand-primary-hover: #1d4ed8;
  --color-focus-ring: rgb(37 99 235 / 0.35);

  /* Ênfase neutra (ações fortes, “ir ao artefato”) */
  --color-cta-emphasis: #111827;
  --color-cta-emphasis-contrast: #ffffff;

  /* Estados */
  --color-nav-active-bg: rgb(37 99 235 / 0.12);
  --color-nav-active-fg: var(--color-brand-primary);

  /* Elevação */
  --shadow-sm: 0 1px 2px rgb(0 0 0 / 0.05);
  --shadow-md: 0 10px 15px -3px rgb(0 0 0 / 0.08);
  --shadow-composer: 0 10px 40px -10px rgb(0 0 0 / 0.12);

  /* Raios */
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 20px;
  --radius-pill: 9999px;

  /* Espaço (escala 4) */
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-3: 0.75rem;
  --space-4: 1rem;
  --space-6: 1.5rem;
  --space-8: 2rem;

  /* Tipografia */
  --font-sans: ui-sans-serif, system-ui, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --text-xs: 0.75rem;
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.125rem;
  --text-xl: 1.25rem;
  --text-2xl: 1.5rem;
  --text-3xl: 1.875rem;

  /* Movimento */
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
}
```

**Notas:**

- **`--color-brand-primary`:** ajustar com pixel-perfect do Figma ou amostra oficial da marca do produto.
- **Plataformas terceiras:** mapear para `--color-platform-linkedin`, etc., quando necessário.
- **Dark mode:** inverter neutros e reduzir sombras; manter `--color-brand-primary` testado para contraste WCAG AA.

### Próximos passos (Brand Guardian)

- Congelar **hex finais** após escolha de marca única (não três azuis concorrentes).
- Adicionar **do’s and don’ts** de logo quando o asset existir.
- Validar **contraste** (texto sobre `bg-muted`, botões, links) com ferramenta automática no CI ou checklist de QA.

**Última revisão (marca/tokens):** 2026-04-10 — baseado em `docs/ui/*.png`, regra Brand Guardian e síntese paralela de análise.

---

**Documento:** unificação de `docs/layout.md` e `docs/brand.md` em `docs/ui-guidelines.md` (2026-04-25).
