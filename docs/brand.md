# Marca e tokens visuais — referências UI

Documento para sustentar uma **branch de front-end** consistente, extraído das imagens em `docs/ui/` no papel **Brand Guardian** (identidade, consistência, tokens). Valores de cor são **inferência visual** até validação com conta-gotas no design final.

## Fontes de referência

| Arquivo | Produto na arte | Contribuição principal à marca |
|--------|-------------------|--------------------------------|
| `docs/ui/version_1.png` | Talk Data to Me | Azul de estado ativo na rail, empty state centrado, pouca sombra |
| `docs/ui/version_2.png` | Maskara.ai | CTA preto, gradientes em preview, sombra suave em card |
| `docs/ui/version_3.png` | Aplot AI | Azul primário tipo produto, pastel em feature cards, glass/soft shadow |
| `docs/ui/auth_1.png` | CoLabs | Azul saturado em CTA/links, logo em pill, split escuro/claro |

---

## Princípios transversais (das referências)

- **Sans-serif neutra** de produto (referência de família: Inter, Geist, SF Pro, system-ui) — alta legibilidade em chat e formulários.
- **Espaço em branco generoso** e hierarquia por peso (semibold/bold em títulos) e cor (texto primário vs. secundário).
- **Cantos arredondados** em escala (chips pill, inputs e cartões 8–24px, painéis hero 24–40px).
- **Profundidade:** alternância entre UI quase flat (`version_1`, formulário em `auth_1`) e **elevação leve** em cards e composer (`version_2`, `version_3`).

---

## Papéis de cor (semântica)

- **Fundo app (camada 0):** branco `#FFFFFF` ou off-white `#F8FAFC` / `#F9FAFB` (variantes entre refs).
- **Superfície levantada:** sidebar, inputs e composer — `#F7F7F7`–`#F9FAFB` ou branco com borda sutil.
- **Texto primário:** preto/carvão `#000000`–`#1E293B`.
- **Texto secundário:** `#666666`–`#64748B`.
- **Bordas / divisores:** `#E0E0E0`–`#E5E7EB`.
- **Ação primária da marca:** família de **azul** (ver conflitos abaixo) ou **preto** para ênfase máxima de ação (`version_2`).
- **Acentos de plataforma:** LinkedIn, tipos de arquivo etc. — sempre tokens `accent-platform-*`, nunca como cor primária da aplicação.

---

## Tabela de aproximações (validar no design)

| Papel sugerido | version_1 | version_2 | version_3 | auth_1 |
|----------------|-----------|-----------|-----------|--------|
| Fundo principal | `#FFFFFF` | ~`#F9FAFB` | ~`#F8FAFC` | `#FFFFFF` (form) |
| Sidebar / superfície | ~`#F7F7F7` | cinza claro | `#FFFFFF` / cinza muito claro | — |
| Estado ativo (nav) | ~`#5072B1`–`#5E7BB5` | cinza em ícone ativo | ~`#F1F5F9` highlight | — |
| CTA / link forte | (sidebar) | `#000000` botão | ~`#2563EB` | ~`#3B4FFE`–`#4353FF` |
| Texto primário | `#000000` | ~`#111827` | ~`#1E293B` | `#000000` |
| Texto secundário | ~`#666666` | ~`#6B7280` | ~`#64748B` | labels ~`#333333` |

---

## Pastéis e feature cards (`version_3`)

Uso decorativo para capacidades (ícones em cápsulas coloridas), não como cor única de marca:

- Verde: fundo ~`#F0FDF4`, ícone ~`#22C55E`
- Azul: ~`#EFF6FF` / ~`#3B82F6`
- Roxo: ~`#FAF5FF` / ~`#A855F7`
- Laranja: ~`#FFF7ED` / ~`#F97316`

---

## Tipografia

- **Família:** uma stack sans moderna; fallback: `system-ui, "Segoe UI", Roboto, sans-serif`.
- **Pesos:** regular (corpo, chat), medium (labels de UI), semibold/bold (títulos, marca).
- **Escala indicativa (px):** 12 (meta, datas), 14–16 (corpo, inputs), 20–24 (títulos de área), 28–40 (hero marketing / welcome).
- **Empty state** costuma ser centralizado; **thread** alinhada à esquerda — variante de layout, não necessariamente escala tipográfica diferente.

---

## Raios (border-radius)

Sistema em múltiplos de **4px** sugere consistência com as refs:

| Token sugerido | Uso |
|----------------|-----|
| `radius-sm` 6px | Pequenos controles, alguns botões secundários |
| `radius-md` 8–12px | Inputs, botões, ícones em squircle |
| `radius-lg` 12–16px | Cards, composer, células de arquivo |
| `radius-xl` 16–24px | Containers grandes, modais |
| `radius-2xl` 24–40px | Painel marketing (`auth_1`), shells “card” |
| `radius-full` | Chips, pills, busca, toggles |

---

## Sombras e elevação

- **Flat:** hierarquia por cor de fundo e borda (`version_1`, formulário `auth_1`).
- **Card flutuante:** sombra difusa baixa opacidade (`version_2` preview social).
- **Soft UI / glass:** `0 10px 15px -3px rgba(0,0,0,0.05)` ou similar (`version_3` — input e cards).

**Diretriz:** reservar sombra a **cards de resultado**, **composer** e **dropdowns**; manter inputs simples sem sombra ou com sombra mínima no foco.

---

## Espaçamento

- **Grid base:** 4px ou 8px (gaps de chips, espaçamento entre label e campo).
- **Padding interno:** ~16–20px em inputs; ~24px+ em cards largos.
- **Seções verticais:** 24–32px entre blocos principais no empty state e no formulário de auth.

---

## Logo e tratamento de marca

- **Persona/avatar** como âncora emocional (`version_1`).
- **Ícone + wordmark** na sidebar e header (`version_2`, `version_3`).
- **Símbolo geométrico + wordmark em pill** (`auth_1`).

Para **content-creator-agent:** documentar **logomark mínimo**, **logotype**, **clear space** e uso opcional de **avatar do agente** sem substituir o logo na navegação principal.

---

## Voz e tom (trechos das artes)

- **Talk Data to Me:** cordial, personificado (“Steven”), instrutivo.
- **Maskara.ai:** objetivo, focado em tarefa e status.
- **Aplot AI:** acolhedor, capacidade (“How Can I Assist You Today?”), upgrade como upsell claro.
- **CoLabs:** acolhimento (“Welcome Back!”) + aspiracional no painel (“Harness Collective Potential.”).

Uniformizar tom de **microcopy** na aplicação alvo conforme posicionamento do produto (ver PRD/spec).

---

## Conflitos entre referências e resolução

1. **CTA primário:** azul de nav (`version_1`) vs **preto** (`version_2`) vs **azul saturado** (`auth_1`).
2. **Fundo:** branco puro vs off-white frio.
3. **Três famílias de azul** distintas se misturadas sem papéis.
4. **Elevação:** flat vs sombra em card/composer.
5. **Densidade de sidebar:** só ícones vs lista + histórico + CTA.

---

## Token set unificado recomendado — content-creator-agent

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

---

## Próximos passos (Brand Guardian)

- Congelar **hex finais** após escolha de marca única (não três azuis concorrentes).
- Adicionar **do’s and don’ts** de logo quando o asset existir.
- Validar **contraste** (texto sobre `bg-muted`, botões, links) com ferramenta automática no CI ou checklist de QA.

**Última atualização:** 2026-04-10 — baseado em `docs/ui/*.png`, regra Brand Guardian e síntese paralela de análise.
