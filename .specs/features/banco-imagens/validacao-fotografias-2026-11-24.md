# Seleção de fotografias e composição — 24/11/2026

- O worker passou a avaliar até dez resultados do Openverse em lotes de cinco
  usando o modelo de visão; formatos não suportados são ignorados e uma resposta
  sem fotografia adequada não publica o job. Imagens e metadados públicos são
  enviados ao provedor do modelo de visão; isso adiciona custo e latência.
- O renderer `3.1.0` dimensiona a superfície opaca ao conteúdo, preserva o
  contraste calculado entre texto e superfície e deixa mais fundo visível. O teste
  Chromium verifica que a superfície cobre menos da metade da área num exemplo
  curto e que conteúdo longo continua sendo rejeitado se ultrapassar o limite.
- Foram geradas duas amostras reais de três slides, com uma imagem na capa, em
  `.local/openverse-real-20261124/melhorado-cafe/` e
  `.local/openverse-real-20261124/melhorado-gatos-2/`. O provedor identificou as
  imagens como CC0: [café](https://commons.wikimedia.org/w/index.php?curid=46261185)
  e [gato](https://commons.wikimedia.org/w/index.php?curid=77710261). A licença
  precisa ser conferida na origem; o Openverse não garante seus metadados.
- Na primeira tentativa da amostra de gatos, a geração estruturada falhou na
  validação de contraste; a segunda tentativa concluiu. Na capa gerada, a área de
  texto ainda encobre parte do rosto do gato: a seleção atual não considera
  automaticamente o ponto focal nem o melhor posicionamento do texto.
- A suíte do worker e o ensaio completo com LocalStack e Openverse simulado
  passaram. O ensaio real usa OpenAI, Openverse e S3 reais; os objetos temporários
  dos jobs foram removidos e os artefatos de avaliação permanecem locais.
