# Layout e padrões de UI — referências

Documento de contextualização para o front-end, derivado das imagens em `docs/ui/` e alinhado aos papéis **UI Designer** e **UX Architect** (estrutura, hierarquia, fundação técnica).

## Fontes de referência

| Arquivo | Produto na arte | Foco principal |
|--------|------------------|----------------|
| `docs/ui/version_1.png` | Talk Data to Me | Empty state centrado, chips de prompt, sidebar com estado ativo |
| `docs/ui/version_2.png` | Maskara.ai | Thread com mensagens, cards de arquivo, preview rico (ex.: LinkedIn), composer |
| `docs/ui/version_3.png` | Aplot AI | Sidebar expandida (busca, histórico, CTA), top bar, cards de recurso, glass/soft UI |
| `docs/ui/auth_1.png` | CoLabs | Auth em coluna dupla: formulário + painel marketing escuro |

Use este arquivo junto com `docs/brand.md` para tokens visuais e decisões de marca.

---

## Visão geral do padrão de produto

As quatro referências convergem em um **aplicativo de conversa com IA** em estilo SaaS:

- **Coluna esquerda fixa** (rail ou sidebar) para navegação global e, em variantes mais ricas, busca e histórico.
- **Área principal** com thread de chat ou **empty state** centrado (persona, título, atalhos).
- **Composer** na base (fixo ou “sticky”), largo, cantos arredondados, com anexos e ações secundárias (enviar, voz, modos).
- **Auth** em tela cheia com **split** formulário claro × marketing visual escuro (quando aplicável).

---

## Shell global (sidebar + main)

- **Rail estreita** (`version_1`, `version_2`): fundo cinza muito claro, separação sutil da área principal (borda ou contraste leve). Main em branco ou off-white.
- **Sidebar rica** (`version_3`): logo + busca em pill, lista de navegação (Home, Explore, Library…), seção **History** (“Today” com itens truncados), card **Upgrade** no rodapé.
- **Main**: conteúdo do chat com coluna de leitura implícita; empty state centralizado (`version_1`, `version_3`); em conversa, fluxo vertical com possível `max-width` central para legibilidade (`version_2`).

**Implementação sugerida:** `display: flex` — sidebar `flex: 0 0 [largura]`; main `flex: 1` e `min-width: 0` para overflow e scroll da thread.

---

## Navegação e icon rail

- **Agrupamento vertical:** topo (marca / menu), meio (ações primárias), base (configurações, créditos, avatar).
- **Estado ativo:** fundo preenchido em squircle ou retângulo arredondado (azul em `version_1`; cinza claro em `version_2` / `version_3` conforme a arte).
- **Inativos:** ícones em linha, cor neutra; alguns controles com borda leve (`+` em `version_1`).
- **Variante “produto completo”** (`version_3`): ícone de grade para menu expandido; item de lista com ícone + label (não só ícones).

Regra de produto: **um contexto ativo** por vez na rail (ex.: Home vs. Library).

---

## Área de chat

### Empty state

- Avatar ou ícone de persona grande, título e subtítulo (`version_1`: “Talk Data to Me” + instrução para escolher prompt).
- Bloco **“Ask about:”** com **chips** (pills) e link para biblioteca de prompts (`version_1`).
- **Hero alternativo** (`version_3`): ícone com glow, headline “How Can I Assist You Today?”, fileira de **feature cards** (capabilities em grid horizontal).

### Conversa

- **Cabeçalho** com nome do produto e chevron (`version_2`) — candidato a seletor de workspace/modelo.
- **Usuário:** mensagens à direita, bolhas em cinza claro (`version_2`).
- **Assistente:** à esquerda; texto mais “plano” ou com anexos como **cards de arquivo** (ícone por tipo, nome).
- **Conteúdo rico:** container externo com gradiente suave; card branco interno; CTAs na base alinhados à direita (`version_2`, preview estilo rede social).

### Top bar (variante densa)

`version_3`: seletor de modelo, **New Chat** (botão escuro), **Export Chat**, avatar — útil como padrão quando o escopo incluir export e troca de modelo sem esconder tudo no header do chat.

---

## Composer / barra de entrada

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

---

## Auth e marketing split (`auth_1`)

- **Coluna esquerda:** logo em pill, “Welcome Back!”, labels acima dos campos, inputs com fundo cinza claro, toggle Remember me, link Forgot password, CTA primário full-width, OAuth (Google), rodapé com Sign up.
- **Coluna direita:** painel escuro com ilustração 3D, headline + parágrafo, **dots de carrossel** na base; cantos muito arredondados no painel.

**Desktop:** grid ou flex 1fr 1fr. **Mobile:** empilhar colunas; painel marketing recolhível, oculto ou em segundo passo.

---

## Grid, flex e breakpoints

- **Thread:** coluna flex; `align-self: end` para usuário, `start` para assistente.
- **Chat central:** `max-width` + `margin-inline: auto` para linha de leitura confortável.
- **Feature cards** (`version_3`): grid horizontal com wrap em telas menores.
- **Breakpoints:** colapsar rail para **drawer** ou **bottom nav**; reduzir padding; chips em wrap; cards ricos com scroll interno se necessário.

---

## Inventário de componentes (nomes sugeridos)

**Shell:** `AppShell`, `SidebarRail`, `SidebarExpanded` (variante com busca/histórico), `NavItem`, `NavIcon`, `BrandMark`, `UserMenuAvatar`.

**Chat:** `ChatLayout`, `ChatHeader`, `ChatThread`, `ScrollArea`, `EmptyChatState`, `PersonaHero`, `PromptChip`, `PromptLibraryLink`, `MessageBubbleUser`, `MessageAssistant`, `AttachmentFileCard`, `RichPreviewCard` (gradiente + inner card + ações).

**Composer:** `ComposerBar`, `ComposerTextField`, `ComposerToolbar`, `AttachmentButton`, `SendButton`, `CharacterCounter`, `VoiceButton`, `ModeChip` (Reasoning, etc.).

**Produto denso:** `TopActionBar`, `ModelSelector`, `FeatureCard`, `HistorySection`, `SearchField`, `UpgradeCard`.

**Auth:** `AuthSplitLayout`, `AuthFormColumn`, `MarketingPanel`, `LabeledInput`, `PasswordInput`, `RememberMeToggle`, `PrimaryButton`, `OAuthButton`, `CarouselDots`.

---

## UX Architect: IA, tema e foco

- **Informação:** rail = navegação global persistente; main = contexto da conversa; empty state = onboarding + atalhos; header com nome do produto pode agrupar troca de workspace/modelo.
- **Tema:** as referências são majoritariamente **light**. O padrão do repositório recomenda suporte a **light / dark / system**; posicionar toggle em **Settings** na rail ou no menu de usuário quando não houver padrão visível nas capturas.
- **Ordem de foco (app chat):** itens da rail (topo → meio → base) → chips ou primeiro focável do empty state → composer (anexo → campo → ações à direita). Em thread: região principal scrollável antes do composer fixo; após enviar, manter foco lógico no campo ou no último assistente.
- **Acessibilidade:** anunciar item ativo na rail; landmarks para thread e composer; contraste e alvo de toque ≥ 44px onde possível; suporte a `prefers-reduced-motion` para animações de cards e glow.

---

## Handoff para implementação

1. Fundação: variáveis CSS (ver `docs/brand.md`) + layout flex/grid.
2. Shell + uma variante de sidebar (mínima vs. expandida).
3. Empty state + thread + composer com composição por slots.
4. Auth split como rota isolada.
5. Estados de carregamento, erro e vazio alinhados à hierarquia visual das referências.

**Última atualização:** 2026-04-10 — baseado em `docs/ui/*.png` e síntese de revisão UI/UX.
