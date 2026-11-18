# Catálogo inicial proposto — documento estruturado V1

**Situação:** protótipo sujeito à validação visual pelo responsável; não é um contrato congelado. O contrato está conectado ao pipeline estruturado, protegido por flag desativada por padrão.

| Item | Proposta |
| --- | --- |
| Layouts | `hero`, `editorial`, `quote` |
| Elementos | `text` (papéis `heading`, `body`, `caption`, `cta`) e `image` |
| Fundo | Cor sólida hexadecimal `#RRGGBB` |
| Tipografia | `plus_jakarta_sans` ou `inter`; tamanhos `small`, `medium`, `large`; pesos `regular`, `medium`, `bold`; alinhamentos `left`, `center`, `right` |
| Imagens | `assetId` opaco e ajuste `cover` ou `contain`; autorização do ID é feita pela API e conferida pelo worker, não pelo schema |
| Limites | 1–20 slides por documento; single com exatamente um slide; 1–12 elementos por slide; texto não vazio de até 2.000 caracteres; IDs de até 64 caracteres |

Os 20 slides são um teto técnico provisório alinhado à inferência existente, não uma regra de produto confirmada. IDs de slide são únicos no documento; IDs de elemento são únicos dentro de cada slide e devem permanecer estáveis entre versões quando preservados. A validação aceita apenas propriedades previstas, rejeita URLs e marcação HTML no texto e aceita cores hexadecimais. O renderizador escapa textos e exige assets autorizados; a validação de schema complementa as verificações de segurança e de renderização.

O catálogo não foi avaliado com exemplos reais de marca. Antes de congelar o schema ou habilitar o fluxo, validar composição, limites, legibilidade e estilos com o responsável e registrar eventuais alterações.
