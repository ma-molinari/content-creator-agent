# Tarefas — banco de imagens

O Openverse é a alternativa inicial, pois o Pexels não está emitindo chaves. A
documentação confirma acesso anônimo, mas a consulta real a partir deste ambiente
atingiu timeout; disponibilidade e limites reais precisam de nova validação.
A V3 foi ligada ao fluxo estruturado, atrás da flag desativada por padrão. A
criação e edição foram ensaiadas com Openverse simulado; a integração real e o
aceite visual ainda precisam de validação.

1. **Contrato e provedor:** V3 guarda crédito e origem no snapshot e negocia
   compatibilidade entre API e workers. Contratos e migração foram testados.
2. **Busca segura (parcial):** o cliente consulta anonimamente e filtra
   resultados CC0 do Wikimedia Commons; o download aceita apenas o domínio oficial,
   até 5 MiB e sem redirecionamentos. Busca e download passaram com HTTP simulado;
   seleção automática e integração foram testadas; falta validação com serviço real.
3. **Criação e renderização:** imagem de fundo, superfície legível e cópias
   versionadas validadas no Chromium e no ensaio Docker com provedor simulado.
4. **Edição:** troca de imagem, edição de texto, créditos e histórico validados
   com provedor simulado; conflitos também foram exercitados.
5. **Interface:** referências retiradas do perfil; procedência e licença são
   disponibilizadas como links no conteúdo do assistente, por versão.
6. **Retirada e limpeza (parcial):** novos usos e uploads foram desativados. Um
   comando com reexecução segura passou em PostgreSQL e LocalStack descartáveis,
   preservando um asset em `slides/`; falta executá-lo em cada ambiente após
   atualizar as instâncias antigas e aguardar os jobs ativos.
7. **Integração (parcial):** o ensaio V3 passou com PostgreSQL, LocalStack e
   Openverse/LLM simulados; executar regressão e validar serviço real e aceite
   visual antes de habilitar a flag no ambiente de destino.
