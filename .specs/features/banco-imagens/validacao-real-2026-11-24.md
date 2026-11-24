# Ensaio real Openverse — 24/11/2026

O ensaio usou stack Docker isolada com V3 habilitada, OpenAI, Openverse, Wikimedia
Commons e S3 reais. Os posts e imagens geradas foram mantidos apenas em `.local/`;
os chats de teste e objetos temporários do S3 foram removidos pelo script de ensaio.

- A busca simples e a busca CC0/Wikimedia responderam HTTP 200, mas outras
  consultas retornaram HTTP 500, 503, 504 ou excederam o tempo limite.
- Downloads Wikimedia falhavam com HTTP 403 usando o identificador padrão de
  `httpx`. A identificação do projeto no `User-Agent` permitiu baixar a imagem
  real e concluir duas gerações. O planejamento também confundiu três slides com
  três imagens; exemplos explícitos foram adicionados ao prompt.
- Três carrosséis de três slides, com uma imagem de fundo na capa, foram gerados:
  `cafe-corrigido`, `pausa-corrigida` e `gatos`, em
  `.local/openverse-real-20261124/`. As duas primeiras usaram a mesma obra do
  [Wikimedia Commons](https://commons.wikimedia.org/w/index.php?curid=78161652),
  identificada como de Wilhelm Bendz; a terceira usou uma
  [obra identificada como de Jean-Baptiste-Siméon Chardin](https://commons.wikimedia.org/w/index.php?curid=174989296).
  O provedor informou CC0; o Openverse não garante a precisão da licença e a
  licença deve ser conferida na origem antes do uso.
- O título da primeira obra veio com HTML e metadados ocultos. A limpeza desses
  campos foi adicionada antes da terceira amostra. Os metadados das primeiras
  duas amostras foram salvos antes dessa correção.
- Avaliação inicial: a seleção do primeiro resultado não garante pertinência ao
  pedido nem variedade; as duas primeiras amostras repetiram uma pintura. A
  superfície opaca ocupa a maior parte da capa, deixando pouca imagem visível.
  O resultado visual permanece sujeito ao aceite do responsável.
- Os testes detectaram uma regressão anterior que poderia expor texto interno de
  erro de edição; o tratamento foi restaurado para mensagens fixas e seguras.

A flag foi ativada somente na stack isolada de ensaio. A disponibilidade real,
o ranking das imagens e a qualidade visual precisam ser avaliados antes de ativar
o recurso em tráfego de produção.
