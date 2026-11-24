# Validação para beta — Openverse

Data: 24/11/2026. Ambiente: Docker isolado com V3 habilitada, PostgreSQL,
Openverse, Wikimedia, OpenAI e S3 reais. Esta validação não habilita a integração
em outros ambientes nem constitui implantação em produção.

## Fluxo real por API

- Criação de post com fotografia de café: concluída com crédito no snapshot.
- Edição de título: concluída; imagem e crédito preservados.
- Troca por fotografia de natureza: concluída; nova imagem e crédito, com título
  preservado. As três versões ficaram disponíveis e a primeira permaneceu
  idêntica byte a byte. O pedido de natureza era genérico, portanto não avalia
  precisão para uma espécie ou paisagem específica.
- Tentativa de editar usando base antiga: rejeitada com HTTP 409.
- URLs assinadas das três versões: JPEGs 1080 × 1350 baixados com sucesso.
- O chat e os objetos S3 dos jobs foram removidos após o ensaio. A conta sintética
  permanece no banco: não foi removida diretamente, pois sua identificação precisa
  e a ausência de dados associados não foram confirmadas.
- Amostras locais: `.local/openverse-real-20261124/beta-edicao-real/`.

## Verificações automatizadas

- `go test ./...` na API: passou.
- Build e testes do frontend: passaram; 24 testes em oito arquivos.
- A suíte do worker com a instrumentação passou no Docker: 353 testes passaram e
  um foi ignorado, incluindo testes no Chromium. O ensaio V3 com Postgres, LocalStack,
  Openverse e LLM simulados cobriu criação, edição, conflito e falha do provedor.

## Interface com serviços reais

Cadastro, login e preenchimento do perfil passaram no navegador. A primeira
geração de café falhou por não encontrar fotografia adequada e apresentou mensagem
compreensível. O botão de tentar novamente iniciou outro job, que falhou com
mensagem genérica segura de geração estruturada. Os logs mostram `ValueError`
após a busca e não identificam a causa. Não se deve interpretar a falha de seleção
como comprovação de que o Openverse estava indisponível.
O frontend reconstruído foi conferido em 1280 × 720 e 390 × 844: aviso do
Openverse e texto corrigido de anexos estavam visíveis. Um novo pedido simples
de fotografia de café também falhou sem encontrar candidata adequada. Após a
reinicialização do worker com os novos eventos de diagnóstico, uma nova criação
de post único de café iniciada no navegador concluiu com slide e créditos visíveis;
as falhas anteriores continuam relevantes para a estabilidade. Com outro
post real criado por API e aberto no navegador, passaram visualização dos créditos
e links, download de ZIP com JPEG, edição de texto, troca de imagem, histórico e
créditos das versões anteriores.
Os chats dos ensaios foram removidos; uma segunda conta sintética permanece no banco.

## Operação e limites

- O banco da stack de teste tinha zero linhas em `user_profile_references`;
  isso não comprova ausência de objetos órfãos no S3 nem cobre outros ambientes.
- Após excluir o chat do ensaio de interface, permaneceram objetos nos três
  prefixos dos jobs; a limpeza imediata é best-effort e a reconciliação estava
  desativada no ambiente. Os objetos de teste identificados foram tratados no
  encerramento do ensaio. A verificação de referências cruzadas foi posterior à
  exclusão: não foram encontrados vínculos ativos, e não havia post_versions
  restantes no banco de teste. Depois da última criação pela interface, dois
  objetos permaneceram no prefixo do job `ba9347c0-2a54-4d92-9b30-576058898c40`;
  o chat foi removido e não houve exclusão direta desses objetos. Antes do beta,
  planejar a reconciliação durável e seu
  prazo mínimo de segurança conforme o runbook; não prometer exclusão imediata.
- A busca anônima tem timeout de 10 segundos, sem retentativa automática nem
  tratamento de `Retry-After`. Houve falhas reais em ensaios anteriores; não há
  medição suficiente para afirmar disponibilidade ou taxa de sucesso. Aplique
  rollout controlado e monitore falhas, duração e custos antes de ampliar o uso.
- Uma consulta sentinela confirmou que o log HTTPX em INFO registrava a URL de
  busca. O worker agora suprime INFO/DEBUG de HTTPX e HTTPCore no startup e emite
  eventos de busca e seleção com resultado, categoria e duração, sem consulta ou
  URL. Testes cobrem o handler direto e propagação. Logs anteriores à correção
  podem conter consultas e devem ser tratados conforme a política do ambiente;
  o agregador existente ainda não processa os novos eventos.
- O Openverse informa limites de acesso e exige respeitá-los: consulte a
  [documentação de autenticação e limites](https://docs.openverse.org/api/reference/authentication_and_throttling.html).
  A consulta gerada pode conter dados pessoais e é enviada ao provedor externo.
- Os [termos do Openverse](https://docs.openverse.org/terms_of_service.html)
  exigem indicar o uso da API e a ausência de endosso ou certificação; o aviso
  foi adicionado à interface. Os metadados CC0 são um filtro inicial: a licença
  e os direitos devem ser conferidos na página de cada obra antes de publicar.
- Antes de ativar em outro ambiente, validar configuração, limpeza de referências,
  URLs assinadas, coleta de métricas e procedimento de rollback descritos no
  runbook. Definir metas de duração, falhas, custo e responsáveis pela operação.
  A compatibilidade V3 deve permanecer disponível para editar versões já criadas.
