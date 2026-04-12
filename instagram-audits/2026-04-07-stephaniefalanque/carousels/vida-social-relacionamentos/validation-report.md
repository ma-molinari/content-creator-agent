# Pré-validação — `vida-social-relacionamentos`

**Pasta:** `instagram-audits/2026-04-07-stephaniefalanque/carousels/vida-social-relacionamentos/`  
**Audit de referência:** `instagram-audits/2026-04-07-stephaniefalanque/AUDIT.md`  
**BRAND (tom/pilares):** `BRAND.md` — jovens adultas, autonomia e limites, vínculos, TCC/DBT implícito no conteúdo.  
**Script:** `node scripts/export-slides.js --validate` → `slide-01-preview.jpg` … `slide-06-preview.jpg`.

## Checklist derivado do AUDIT.md

| Critério | Avaliação |
|----------|-----------|
| Paleta (magenta, rosa poeira, papel, grafite) | Alinhado — mesmos tokens que carrosséis existentes do mesmo audit. |
| Lockup topo (@handle // Psicóloga de Jovens Adultas) | Presente em todos os slides (variante A). |
| Zona segura inferior (~276px) | Texto principal e CTA em vidro ancorados acima; numeração `NN / 06` visível acima da faixa de UI. |
| Estilo "terapia acessível" | Faixas com rotação leve, fundos papel / pink-wash / foto humana — coerente com amostra auditada. |
| Painéis escuros | `block-dark` / `note-box` com fundo semitransparente + blur — não preto chapado. |
| Miolo vertical (slides pouco densos) | Slides 02 e 05 usam `slide__body-centered` com conteúdo centrado na área útil. |
| Humanização — fotos de fundo | Slides 01, 03 e 06 receberam fotos Unsplash (licença livre) sob o overlay de gradiente; slides de papel (02, 04, 05) mantêm textura sólida para legibilidade máxima. |

## Fotos de fundo adicionadas (iteração 2)

| Slide | Classe modificadora | Foto (Unsplash — licença livre) | Tamanho preview |
|-------|---------------------|---------------------------------|-----------------|
| 01 | `.photo-bg--social` | "A group of friends laughing together outdoors" — Ufoma Ojo (`photo-1755705152604-af6804fb8932`) | 258 KB — confirma carregamento |
| 03 | `.pink-wash--introspective` | "Woman in cozy sweater sits by warm window light" — Roman Manshin (`photo-1767439565605-628d6e875b7b`) | 130 KB |
| 06 | `.pink-wash--connection` | "Two women talking at an outdoor cafe table" — Vitaly Gariev (`photo-1758274252296-a63b1d7d4bb8`) | 122 KB |

Gradientes de marca mantidos como camada superior (opacidade 22–72%) para garantir legibilidade dos textos e coerência da paleta magenta/rosa do audit.

## Por slide

| Slide | Resultado | Notas |
|-------|-----------|--------|
| 01 | **pass** | Gancho com quatro faixas + rosa; kicker legível; foto de amigas rindo garante humanização no scroll. Lockup claro sobre gradiente escuro. |
| 02 | **pass** | Papel, faixas magenta, corpo educativo; tag "1 · Corpo e convívio". |
| 03 | **pass** | Pink-wash sobre foto introspectiva (mulher junto à janela, pensativa); `note-box` em vidro sobre a foto. Alinhado ao tema "não sou boa o suficiente". |
| 04 | **pass** | Limites / dizer não + callout rosa "Na prática"; hierarquia clara. |
| 05 | **pass** | Lista com bullets magenta; disclaimer educativo em itálico. |
| 06 | **pass** | CTA com foto de duas mulheres conversando em café — reforça o convite ao DM. `.final-cta-mid` sem sobreposição; vidro centrado no rodapé. |

## Resumo

Conjunto **aprovado para revisão editorial** — fotos humanizadas em slides 01, 03 e 06 (iteração 2). Export final `slide-XX.jpg` só após confirmação explícita do utilizador no chat (Phase E do skill).
