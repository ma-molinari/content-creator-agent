# Tarefas — banco de imagens

O Openverse é a alternativa inicial, pois o Pexels não está emitindo chaves. A
documentação confirma acesso anônimo, mas a consulta real a partir deste ambiente
atingiu timeout; disponibilidade e limites reais precisam de nova validação.
A busca inicial foi implementada e validada com HTTP simulado, mas ainda não foi
ligada ao fluxo de posts; as demais atividades continuam pendentes.

1. **Contrato e provedor:** definir limites e condições do provedor, guardar
   metadados de crédito e origem por versão e negociar compatibilidade entre API e
   worker. Validar contratos entre serviços e versões anteriores.
2. **Busca segura (parcial):** cliente inicial consulta anonimamente e filtra
   resultados CC0 do Wikimedia Commons; o download aceita apenas o domínio oficial,
   até 5 MiB e sem redirecionamentos. Busca e download passaram com HTTP simulado;
   faltam seleção automática, integração e validação com serviço real acessível.
3. **Criação e renderização:** incorporar imagens autorizadas ao documento e
   adicionar composição de fundo com texto legível; manter cópias versionadas
   conforme as condições do provedor. Validar slides e renderização no Chromium.
4. **Edição:** selecionar e substituir imagens solicitadas preservando demais
   elementos e versões anteriores; verificar conflitos e indisponibilidade.
5. **Interface (parcial):** referências retiradas do perfil; faltam procedência e
   créditos das imagens utilizadas e validação do fluxo de criação e troca.
6. **Retirada e limpeza (parcial):** novos usos e uploads foram desativados. Um
   comando com reexecução segura passou em PostgreSQL e LocalStack descartáveis,
   preservando um asset em `slides/`; falta executá-lo em cada ambiente após
   atualizar as instâncias antigas e aguardar os jobs ativos.
7. **Integração:** executar suites e ensaio Docker de ponta a ponta, atualizar
   documentação e registrar limitações de operação e licença.
