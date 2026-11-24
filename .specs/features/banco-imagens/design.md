# Integração Openverse — desenho em implementação

## Contrato V3

O snapshot V3 estende o conteúdo V2 com fundo sólido ou fundo por `assetId` e um
mapa de créditos por asset. O manifesto existente continua associando IDs a chaves
imutáveis em `slides/{job}/assets/`; fundos também devem constar no manifesto.
Versões V1/V2 podem ser promovidas para V3 sem modificar o snapshot anterior.
Créditos de assets ainda usados devem sobreviver à edição; os de assets removidos
são excluídos apenas do novo snapshot.

O renderer usa um fundo fotográfico e uma superfície opaca na cor do fundo para o
texto, de modo que a validação de contraste continue calculável. API e worker
validam separadamente o documento e os IDs. A migração de jobs aceita a versão 3
e bloqueia rollback enquanto existirem jobs ou versões V3.

## Integração e pendências

- A API negocia capacidades V3 com todos os workers elegíveis e impede downgrade;
  `STRUCTURED_STOCK_IMAGES_ENABLED` ativa a seleção para novas versões. Os jobs
  V3 promovem versões antigas e publicam assets e créditos de forma imutável.
- A busca recebe uma consulta gerada pelo modelo a partir do pedido; o prompt pede
  que ela não contenha dados pessoais, mas isso não é uma garantia automática.
- Créditos e links são exibidos no conteúdo do assistente. O Openverse não garante
  a precisão das licenças; o usuário deve conferir a origem antes de usar a imagem.
- O fluxo Docker com provedor simulado cobriu criação, edição, histórico e conflito;
  a criação com provedor real foi exercitada com intermitência. A edição real e o
  aceite visual no ambiente alvo permanecem pendentes.
