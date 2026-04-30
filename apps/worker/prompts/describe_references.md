# Referências visuais

Analise as imagens fornecidas como **referências de design** (moodboard / estilo) para o carrossel. Não invente dados sobre a marca; descreva apenas o que vê e infere de forma prudente sobre estética e execução.

Distinga, quando fizer diferença, **superfície gráfica** (slide editorial, tipografia no plano) de **cena** (lifestyle, pessoas, locais) ou híbrido. Prefira termos concretos (material, luz no plano, acentos, hierarquia) a adjetivos vagos sozinhos.

## Objetivo para o pipeline (acionável em HTML/CSS)

O resumo alimenta agentes que **só recebem texto** — não as imagens. Por isso a saída deve ser **traduzível em CSS** no canvas 1080×1350:

- Sempre que as imagens permitirem, inclua **aproximações de cor em hex** para fundos dominantes, texto principal, **accent** (destaques em manchetes), bordas e overlays — com ressalva “aprox.” quando for estimativa.
- Indique **ritmo entre slides** quando dedutível (ex.: alternância claro/escuro, capa “full bleed” escura vs corpo claro, uso de blocos com cantos arredondados vs reto).
- Descreva **sombras, gradientes, vinhetas e textura implícita** de forma que um front-end possa reproduzir com `box-shadow`, `linear-gradient`, `radial-gradient` ou camadas — sem pedir URLs de imagem.
- **Hierarquia tipográfica:** pesos relativos (ex.: rótulo 600, manchete 800, corpo 500), alinhamento dominante e se o estilo tende a **condensado vs arejado** (relacionável a padding e line-height).

## Saída (Markdown, pt-BR)

Uma **única** resposta com esta estrutura:

## REFERÊNCIAS_VISUAIS (resumo)

- **Tipo e foco** — predominância de layout gráfico/editorial (tipografia, blocos) vs cena fotográfica (lifestyle, estúdio, pessoas) ou ilustração; indique se é mistura.
- **Paleta e contraste** — cores dominantes com **hex aproximado** quando possível; contraste título–fundo e **legibilidade** vs intenção esteticamente suave; fundos claros/escuros e cor de **accent** para realces.
- **Superfície, luz e textura** — em planos desenhados: acabamento (papel mate, grão, painel), luz difusa no plano, sombras, vinhetas. Em cenas/ilustração: estilo, direção e qualidade de luz, mood.
- **Tipografia** — se legível, estilo (sans/serif, peso), alinhamento aproximado; hierarquia aparente (rótulo vs título vs corpo) ou “não legível o suficiente na imagem”; quando útil para o gerador, relacione a **densidade visual** ao espaçamento (arejado vs compacto).
- **Layout, ritmo e leitura** — classifique se a referência é **monocoluna / leitura vertical** (fluxo de cima a baixo) vs **grade multi-coluna** (várias colunas de texto). Indique densidade, espaçamento, ordem em que a composição guia o olho; margens e respiro se evidentes. **Se for multi-coluna (estilo revista):** o gerador em 1080px **não** deve replicar a grade literalmente — anote **paleta, hierarquia, tom e ritmo** para reutilizar; a composição no carrossel deve ser **coluna única** por padrão.
- **Acentos gráficos** — ícones, emojis, selos, linhas, stickers; posição e tratamento (sombra, plano) **sem** inventar texto de marca.
- **Marca e moldura** (apenas o visível) — posição aproximada de logo/marca na imagem, folga às bordas; **não** atribua regras de brand inexistentes no material.
- **Coesão entre referências** — se forem várias imagens, o que se repete (paleta, estilo) e diferenças notáveis.
- **O que NÃO replicar** (se houver) — estética, clichês, poluição visual ou padrões indesejáveis. Se a referência for *layout* multi-coluna, **não** trate a grade como planta a copiar no export móvel — só o que for seguro reutilizar (cores, hierarquia, mood).

Use 1 a 4 bullets concisos por tópico, sem repetir a mesma ideia. Priorize detalhes **replicáveis em CSS**. Tópicos que não se aplicam podem ser omitidos ou respondidos com uma frase curta (ex.: “N/A — cena só fotográfica”).
