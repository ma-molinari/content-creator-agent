# Banco de imagens para posts

## Objetivo

Substituir referências visuais do perfil por imagens obtidas de um serviço gratuito
com API pública. A seleção inicial é automática e o usuário pode solicitar outra
imagem na edição. O Pexels deixou de emitir novas chaves; o Openverse é a
alternativa inicial, com acesso anônimo sujeito a limites. A API identifica
obras de terceiros e não garante a precisão das licenças informadas: a integração
deve preservar a origem e permitir verificar a licença da obra antes do uso.

## Requisitos

- **IMG-01:** Ao criar um post com imagens, buscar imagens pertinentes ao conteúdo
  e permitir sua utilização em slides ou como fundo.
- **IMG-02:** Ao editar um post, permitir substituir uma imagem sem modificar as
  demais; preservar a versão anterior e seus assets.
- **IMG-03:** Guardar origem, licença aplicável e dados de atribuição, quando
  disponibilizados e necessários para atender às regras do provedor.
- **IMG-05:** Restringir a busca inicial a resultados identificados como CC0 e
  deixar acessíveis a origem e os metadados de licença para verificação; não
  tratar os metadados retornados como garantia de direitos.
- **IMG-04:** Proteger credenciais, validar respostas e downloads e apresentar
  falha compreensível se a busca ou o provedor estiver indisponível.
- **REF-01:** Remover do produto o cadastro e o uso de referências visuais do
  perfil, bem como os arquivos de origem e os respectivos registros existentes.
- **REF-02:** Não excluir assets de versões de posts existentes ao remover as
  referências de origem; a limpeza deve ser retomável em caso de falhas.
- **COMP-01:** Manter leitura, download e edição de versões existentes e impedir
  que alterações do contrato sejam interpretadas por workers incompatíveis.

## Validação

Testar criação e troca de imagens com provedor simulado, crédito e origem,
isolamento entre usuários, erros do provedor, limpeza retomável, preservação do
histórico e execução integrada no Docker. A validação contra o serviço real depende
de credenciais e do atendimento às suas condições de uso.
