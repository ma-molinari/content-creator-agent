# Pré-validação — `ansiedade-relacionamentos`

**Pasta:** `instagram-audits/2026-04-07-stephaniefalanque/carousels/ansiedade-relacionamentos/`  
**Audit de referência:** `instagram-audits/2026-04-07-stephaniefalanque/AUDIT.md`  
**BRAND:** `BRAND.md` — jovens adultas, segunda pessoa, vínculos, tom acolhedor; sem promessa de cura no slide de solução.  
**Script:** `node scripts/export-slides.js --validate` → `slide-01-preview.jpg` … `slide-06-preview.jpg`.

## Checklist derivado do AUDIT.md e do plano

Inclui **revisão de usabilidade pós-previews** (Phase D, passo 4 em `create-social-posts/SKILL.md`): contraste de texto sobre foto/lavado, leitura à primeira vista, coerência estética — além do render Playwright (passo 2).

| Critério | Avaliação |
|----------|-----------|
| Paleta (magenta, rosa poeira, papel, grafite) | Alinhado — tokens partilhados com `vida-social-relacionamentos`. |
| Lockup topo (variante A) | Presente em todos os slides. |
| Zona segura inferior (~276px) | Texto principal e CTA em vidro ancorados acima da faixa inferior; **sem** numeração `NN/06` nas imagens (requisito do skill/plano). |
| Estilo "terapia acessível" | Faixas com rotação leve; papel + pink-wash + foto humana. |
| Painéis escuros | `note-box` / `block-dark` com vidro semitransparente + blur. |
| Miolo vertical | Slides com corpo único usam `slide__body-centered`; CTA final usa `.final-cta-mid` + rodapé em vidro. |
| Tema sensível | Disclaimer educativo no slide 05; linguagem de convite, não diagnóstico. |

## Foto de fundo (Unsplash — licença livre)

| Slide | Classe modificadora | Foto |
|-------|---------------------|------|
| 01 | `.photo-bg--relacionamentos` | Andrew Neel — *man and woman holding hands* (`photo-1627486589655-a23ac61c4009`) |
| 03, 06 | `.pink-wash--relacionamentos` | Mesma imagem local `bg-relacionamentos.jpg` sob gradiente rosa/magenta |

## Por slide

| Slide | Resultado | Notas |
|-------|-----------|--------|
| 01 | **pass** | T1: gancho + faixas + parágrafo de apoio em vidro; foto visível sob overlay; lockup legível. |
| 02 | **pass** | T5 papel: problema (loop, antecipação); tag `1 ·` alinhada ao mapa do CTA. |
| 03 | **pass** | Agitação (celular, silêncio); `note-box` legível sobre pink-wash. |
| 04 | **pass** | Desejo (paz, confiança, presença); corpo centrado na área útil. |
| 05 | **pass** | Solução com TCC, “sem promessa mágica”, disclaimer em itálico. |
| 06 | **pass** | CTA denso: legenda numerada fora do vidro grande; vidro com DM, bio, salvar. **Usabilidade:** legenda 1–4 deixou de usar `--dark` sobre foto; passou a **branco** + **painel vidro** (`rgb(24 18 22 / 0.58)` + blur), números `--rose-dust-light`, `font-weight: 700` — legível em zonas claras e escuras do fundo. |

## Resumo

Conjunto **aprovado para revisão editorial**. **Phase E (2026-04-09):** export final executado com confirmação do utilizador — gerados `slide-01.jpg` … `slide-06.jpg` na mesma pasta (qualidade JPEG 92, 768×1376).
