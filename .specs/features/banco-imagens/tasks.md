# Tarefas — banco de imagens

O Openverse é a alternativa inicial, pois o Pexels não está emitindo chaves. A
V3 foi ligada ao fluxo estruturado, atrás da flag desativada por padrão. Em
24/11/2026, criação e download reais foram exercitados em stack isolada, com
intermitência no serviço. A edição com serviços reais foi validada posteriormente;
evidências e limites estão em `validacao-beta-2026-11-24.md`. Metas operacionais,
limpeza em outros ambientes e ativação no ambiente de beta permanecem pendentes.

1. **Contrato e provedor:** V3 guarda crédito e origem no snapshot e negocia
   compatibilidade entre API e workers. Contratos e migração foram testados.
2. **Busca segura (parcial):** o cliente consulta anonimamente e filtra
   resultados CC0 do Wikimedia Commons; o download aceita apenas o domínio oficial,
   até 5 MiB e sem redirecionamentos. Busca e download passaram com HTTP simulado;
   seleção automática foi testada com serviço real, que apresentou intermitência.
3. **Criação e renderização:** imagem de fundo, superfície legível e cópias
   versionadas validadas no Chromium e no ensaio Docker com provedor simulado.
4. **Edição:** troca de imagem, edição de texto, créditos e histórico validados
   com provedor simulado; troca, histórico e conflito também passaram com serviços
   reais em stack isolada.
5. **Interface:** referências retiradas do perfil; procedência e licença são
   disponibilizadas como links no conteúdo do assistente, por versão.
6. **Retirada e limpeza (parcial):** novos usos e uploads foram desativados. Um
   comando com reexecução segura passou em PostgreSQL e LocalStack descartáveis,
   preservando um asset em `slides/`; falta executá-lo em cada ambiente após
   atualizar as instâncias antigas e aguardar os jobs ativos.
7. **Integração (parcial):** o ensaio V3 passou com PostgreSQL, LocalStack e
   Openverse/LLM simulados; a criação também passou com serviços reais. Faltam
   validação operacional no ambiente de destino e metas antes de ampliar o tráfego.
