# Validação da composição focal — 24/11/2026

O renderer V3 posiciona o recorte e o painel de texto para reduzir a sobreposição
com uma região focal estimada pelo modelo de visão. O painel usa a cor de fundo
da paleta com transparência calculada para contraste mínimo de 4,5:1 sobre
qualquer cor da fotografia. Se não houver opacidade translúcida válida para todos
os textos, o job falha. A caixa focal acompanha o snapshot de cada versão; a
primeira edição de um V3 anterior sem caixa calcula uma para a nova versão.

Referências: [W3C, contraste sobre imagens](https://www.w3.org/WAI/WCAG21/Techniques/general/G18),
[MDN, fundos e contraste](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Styling_basics/Backgrounds_and_borders)
e [Cloudinary, áreas focais](https://cloudinary.com/documentation/custom_focus_areas).

## Resultados

- Testes do worker: 340 passaram, 7 ignorados; testes com Chromium no Docker:
  5 passaram. A suíte da API Go passou.
- Ensaio `tests/docker_hybrid/run_v3.py` no Docker: criação, edição, troca,
  créditos, histórico, conflito e falha de provedor passaram com Postgres,
  LocalStack e Openverse simulado.
- Duas amostras de três slides foram geradas com Openverse, OpenAI e S3 reais;
  os JPEGs e snapshots locais estão em `.local/openverse-real-20261124/` nas
  pastas `transparente-gatos-final` e `transparente-cafe-final-2`. No primeiro,
  o rosto do gato ficou visível; no segundo, a xícara ficou majoritariamente
  visível, com pequena sobreposição do painel na parte superior do café.
- A amostra de café inclui a frase operacional “Foto de café no fundo, quando
  disponível no acervo autorizado.” no conteúdo gerado. É um defeito de copy a
  investigar; a amostra serve para avaliar a composição, não a qualidade textual.
- Uma tentativa anterior de café falhou antes da renderização com `worker_exception`;
  a repetição concluiu. A disponibilidade da geração real não é garantida.
- Após os ensaios, a consulta aos prefixos de jobs dos chats de teste não encontrou
  objetos restantes no S3 e não havia jobs ativos no ambiente de teste.

A região focal é aproximada: uma caixa imprecisa, assunto grande ou texto extenso
pode produzir sobreposição. A escolha é limitada às posições e larguras disponíveis;
aprovação estética depende de avaliação humana. A licença e os créditos fornecidos
pelo Openverse devem ser conferidos na fonte.

## Correção de copy e faixa superior

O renderer 3.2.1 impede o colapso da margem do painel que deslocava o fundo e
deixava uma faixa na borda superior. O teste de Chromium verifica as coordenadas
superior e inferior da fotografia. Os prompts de criação e edição agora distinguem
instruções operacionais do texto publicável, sem impedir a publicação quando o
usuário pedir explicitamente; como dependem do modelo, não garantem o resultado.

No Docker, 346 testes do worker passaram e um foi ignorado; o ensaio V3 com
Postgres, Chromium, LocalStack e provedores simulados passou. Duas amostras reais
de três slides estão em `.local/openverse-real-20261124/correcao-cafe/` e
`correcao-paisagem/`: o texto dos seis slides foi revisado e não apresentou
frases operacionais, e as capas não apresentaram a faixa superior. Duas tentativas
de gerar uma amostra de gatos falharam na busca de imagem (`IMAGE_SEARCH_FAILED`).
Após os ensaios, não havia jobs ativos nem objetos restantes nos prefixos dos
jobs dos chats de teste no S3.
