---
name: map-instagram-profile
description: >-
  Defines folder layout, file naming, and minimum capture set for Instagram
  profile audits using screenshots and plain-text bios/captions (no Instagram
  API). Organizes material under instagram-audits/YYYY-MM-DD_username/ by
  surface (meta, profile, highlights, grid, posts, reels, optional stories).
  Use when creating or restructuring an audit folder, naming capture files,
  planning screenshot-based profile documentation, or before curator-style
  analysis. Triggers: auditoria Instagram, capturas de perfil, estrutura
  instagram-audits, mapear perfil Instagram, screenshot audit, pasta de
  auditoria. Content analysis (palette, grid, voice) follows
  marketing-instagram-curator — this skill covers file organization only.
---

# Map Instagram profile (screenshot audit layout)

**Scope:** Organize **captures de tela e texto** (bio, grade, posts abertos, Reels, highlights, Stories opcionais) para reduzir dependência de API e risco de automação. **Não** cobre a análise semântica/estratégica (paleta, grade, tom de voz): isso fica em [.cursor/rules/marketing/marketing-instagram-curator.md](../../rules/marketing/marketing-instagram-curator.md).

**Alinhamento:** Pastas `instagram-audits/<data>-<handle>/` são as mesmas usadas por [create-social-posts](../create-social-posts/SKILL.md) (`AUDIT.md`, `BRAND.md`, carrosséis). Esta skill define **onde** colocar capturas e legendas; não exige Playwright nem export JPG.

---

## Princípios

1. **Um perfil = uma pasta raiz** com **data da captura** no nome (o feed muda; versionar no tempo).
2. **Separar por superfície:** perfil, highlights, grade, posts, Reels, Stories (só se ainda ativas e relevantes).
3. **Nomes ordenáveis:** prefixos `01_`, `02_` ou `YYYY-MM-DD_`; padrão estável em todo o conjunto.
4. **Bio e legendas em `.md` ou `.txt`** — busca, relatórios e prompts funcionam melhor que só imagem.

---

## Raiz e árvore

Crie a raiz onde fizer sentido (ex.: `instagram-audits/` na raiz do repositório). **Substitua** `YYYY-MM-DD` e `username` pelos valores reais. Caminhos relativos à pasta do perfil `instagram-audits/YYYY-MM-DD_username/`:

```text
instagram-audits/
└── YYYY-MM-DD_username/
    ├── 00_meta/
    │   ├── profile_url.txt
    │   ├── captured_at.txt
    │   └── notes.md
    ├── 01_profile/
    │   ├── 01_profile_full.png
    │   ├── 02_avatar.png
    │   └── bio.txt
    ├── 02_highlights/
    │   ├── cover_<slug>.png
    │   └── ...
    ├── 03_grid/
    │   ├── 01_grid_top.png
    │   ├── 02_grid_scroll_01.png
    │   └── ...
    ├── 04_posts/
    │   ├── p001_carousel_slide01.png
    │   ├── p001_carousel_slide02.png
    │   ├── p001_caption.txt
    │   ├── p002_single.png
    │   ├── p002_caption.txt
    │   └── ...
    ├── 05_reels/
    │   ├── r001_cover.png
    │   ├── r001_caption.txt
    │   └── ...
    └── 06_stories/
        └── ...
```

| Pasta / ficheiro | Conteúdo |
| ---------------- | -------- |
| `00_meta/profile_url.txt` | URL exata do perfil |
| `00_meta/captured_at.txt` | Data/hora, fuso, dispositivo (web / iOS / Android) |
| `00_meta/notes.md` | Cliente, benchmark, idioma, objetivo da análise |
| `01_profile/01_profile_full.png` | Bio + avatar + stats + highlights (área principal visível) |
| `01_profile/02_avatar.png` | Opcional: recorte do avatar |
| `01_profile/bio.txt` | Texto da bio copiado |
| `02_highlights/cover_<slug>.png` | Uma capa por highlight visível |
| `03_grid/01_grid_top.png` | Primeiras 2–3 linhas da grade |
| `03_grid/02_grid_scroll_01.png` | Continuação conforme necessário |
| `04_posts/pNNN_*` | Posts abertos: `pNNN_single.png`, `pNNN_carousel_slideNN.png`, `pNNN_caption.txt` |
| `05_reels/rNNN_cover.png` + `rNNN_caption.txt` | Miniatura + legenda |
| `06_stories/` | Opcional; só se ativas e relevantes para a análise |

---

## Convenções de nome

`NNN` em `pNNN` e `rNNN` é **sempre três dígitos** (`001`, `002`, …) para ordenação estável. A **ordem dos ficheiros** por nome deve refletir a **ordem de leitura** na grade.

| Elemento | Convenção |
| -------- | ----------- |
| Pasta do perfil | `instagram-audits/YYYY-MM-DD_username/` |
| Post único | `04_posts/pNNN_single.png` + `04_posts/pNNN_caption.txt` |
| Carrossel | `pNNN_carousel_slide01.png` … `slideNN.png` + `pNNN_caption.txt` |
| Reels | `05_reels/rNNN_cover.png` + `05_reels/rNNN_caption.txt` |
| Highlights | `02_highlights/cover_<slug>.png` ou `hl01_cover.png` se o slug não for claro |

---

## Conjunto mínimo recomendado

Checklist antes de fechar a pasta ou enviar para análise:

- [ ] **`01_profile/`:** `01_profile_full.png` e `bio.txt`
- [ ] **`03_grid/`:** pelo menos **9–12** miniaturas nítidas (`01_grid_top.png` e scrolls adicionais se preciso)
- [ ] **`04_posts/`:** **6–12** posts representativos com **`pNNN_caption.txt`** quando houver legenda
- [ ] **`05_reels/`:** **3–6** pares `rNNN_cover.png` + `rNNN_caption.txt`
- [ ] **`00_meta/`:** `profile_url.txt`, `captured_at.txt`, `notes.md`

Opcional: **`02_highlights/`** com capas; **`06_stories/`** quando fizer sentido.

---

## Boas práticas

- Capturas na **resolução nativa**, zoom **100%** no browser quando aplicável (cor e tipografia).
- **Um ficheiro de legenda por post** — evita misturar conteúdos e facilita prompts e revisão.
- Nova auditoria no tempo: **duplicar** a pasta raiz com **nova data** em vez de sobrescrever.

---

## Próxima etapa: análise

Com `instagram-audits/YYYY-MM-DD_username/` preenchida, aplicar **[Marketing Instagram Curator](../../rules/marketing/marketing-instagram-curator.md)** — paleta, fotografia, ritmo da grade, mix de formatos, tom de voz, CTAs, highlights como arquitetura de marca.
