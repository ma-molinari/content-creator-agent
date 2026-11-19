# Catálogo inicial aprovado — documento estruturado V1

**Situação:** catálogo inicial V1 aprovado pelo responsável após análise das amostras em 2026-11-18. O contrato está conectado ao pipeline estruturado, protegido por flag desativada por padrão. Alterações incompatíveis devem ser tratadas por versionamento.

| Item | Catálogo V1 |
| --- | --- |
| Layouts | `hero`, `editorial`, `quote` |
| Elementos | `text` (papéis `heading`, `body`, `caption`, `cta`) e `image` |
| Fundo | Cor sólida hexadecimal `#RRGGBB` |
| Tipografia | `plus_jakarta_sans` ou `inter`; tamanhos `small`, `medium`, `large`; pesos `regular`, `medium`, `bold`; alinhamentos `left`, `center`, `right` |
| Imagens | `assetId` opaco e ajuste `cover` ou `contain`; autorização do ID é feita pela API e conferida pelo worker, não pelo schema |
| Limites | 1–20 slides por documento; single com exatamente um slide; 1–12 elementos por slide; texto não vazio de até 2.000 caracteres; IDs de até 64 caracteres |

Os 20 slides são um teto técnico V1 alinhado à inferência existente, não uma regra de produto confirmada. IDs de slide são únicos no documento; IDs de elemento são únicos dentro de cada slide e devem permanecer estáveis entre versões quando preservados. A validação aceita apenas propriedades previstas, rejeita URLs e marcação HTML no texto e aceita cores hexadecimais. O renderizador escapa textos e exige assets autorizados; a validação de schema complementa as verificações de segurança e de renderização.

A aprovação considerou as amostras genéricas de `visual/`, sem imagens de marca. A ativação continua sujeita à aceitação operacional, incluindo ensaio com infraestrutura real e definição de metas de rollout.
