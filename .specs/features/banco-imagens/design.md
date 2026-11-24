# Integração Openverse — desenho do beta

## Contrato V3

O snapshot V3 estende o conteúdo V2 com fundo sólido ou fundo por `assetId` e um
mapa de créditos por asset. O manifesto existente continua associando IDs a chaves
imutáveis em `slides/{job}/assets/`; fundos também devem constar no manifesto.
Versões V1/V2 podem ser promovidas para V3 sem modificar o snapshot anterior.
Créditos de assets ainda usados devem sobreviver à edição; os de assets removidos
são excluídos apenas do novo snapshot.

O renderer usa um fundo fotográfico e uma superfície translúcida na cor do fundo,
com opacidade calculada para garantir o contraste e posicionamento orientado pela
caixa focal estimada da imagem. API e worker
validam separadamente o documento e os IDs. A migração de jobs aceita a versão 3
e bloqueia rollback enquanto existirem jobs ou versões V3.

## Integração e pendências

- A API negocia capacidades V3 com todos os workers elegíveis e impede downgrade;
  `STRUCTURED_STOCK_IMAGES_ENABLED` ativa a seleção para novas versões. Os jobs
  V3 promovem versões antigas e publicam assets e créditos de forma imutável.
- A busca recebe uma consulta gerada pelo modelo a partir do pedido; o prompt pede
  que ela não contenha dados pessoais, mas isso não é uma garantia automática.
  O worker avalia até dez candidatos públicos em lotes de cinco pelo modelo de
  visão, priorizando fotos pertinentes. Na ausência de candidata, tenta até duas
  buscas mais genéricas avaliadas contra o tema original. Em criação com foto
  opcional, ausência de candidata ou falha ao obter imagem gera post com fundo
  sólido e aviso; em edição ou pedido explícito, a operação falha sem nova versão.
  Essa etapa adiciona custo e latência e não garante relevância.
- Créditos e links são exibidos no conteúdo do assistente. O Openverse não garante
  a precisão das licenças; o usuário deve conferir a origem antes de usar a imagem.
- O fluxo Docker com provedor simulado cobriu criação, edição, histórico e conflito;
  criação e edição com serviços reais foram exercitadas em ambiente de teste, com
  falhas intermitentes. O responsável aceitou o beta para o projeto open source em
  24/11/2026, com as limitações registradas em `validacao-beta-2026-11-24.md`.
  Isso não comprova implantação nem validação em outro ambiente de destino.
