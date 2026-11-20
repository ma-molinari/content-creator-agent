# Evidências de validação — geração híbrida

## Ambiente local

- Catálogo V1 aprovado pelo responsável em 2026-11-18, com amostras genéricas e fontes reais; não equivale a ensaio com marca real.
- Suíte Go unitária e integração completa com PostgreSQL temporário: passaram, incluindo concorrência, isolamento, rollback, callback com resposta perdida e recuperação de limpeza em processo separado.
- Integração API HTTP + worker HTTP + PostgreSQL e Chromium real: passou para criação, edição, imagem herdada após remoção da referência original e pedido de edição não suportado. LLM e S3 foram simulados.
- Worker: 197 testes passaram; dois testes opcionais de Chromium foram executados separadamente na validação anterior. Agregador local de métricas: dois testes passaram.
- Frontend: 17 testes e build passaram na validação anterior; não houve alterações no frontend nesta etapa.

## Ensaio Docker isolado

- Ensaio reproduzível por `python tests/docker_hybrid/run.py`: API, worker e PostgreSQL executados em containers temporários; S3 foi simulado em memória com endpoint HTTP local, a LLM foi simulada e o Chromium usou uma fonte de teste. Passaram criação com anexo, edição após remoção da origem da imagem, histórico e downloads.
- Cliente antigo e outro usuário foram bloqueados; duas edições concorrentes tiveram uma vencedora e um conflito. Uma resposta de callback foi descartada após o commit, seguida de retentativa sem versão duplicada. Após reiniciar a API com a flag desligada, um novo chat foi criado no formato legado e um chat estruturado preexistente foi editado com sucesso.
- A rotina de reconciliação foi interrompida enquanto o S3 simulado estava pausado. Após reinício, removeu os objetos simulados pendentes e manteve os inventários. A agregação dos logs da API identificou dois jobs estruturados concluídos; essa amostra não define metas.
- Containers, rede e arquivos temporários do ensaio foram removidos. O Docker Desktop foi iniciado e permaneceu disponível.

## LocalStack para desenvolvimento

O LocalStack 3.8.1 foi iniciado no Docker com bucket `postmind-local`. Foram verificadas escrita, leitura e exclusão pelo cliente Python e pelo cliente Go na rede Docker, acesso a URL assinada pelo host e escrita imutável do worker, incluindo rejeição de conteúdo divergente. O overlay `docker-compose.localstack.yml` reproduz a configuração. O ensaio Docker com `HYBRID_DOCKER_S3=localstack` também passou para criação, imagem herdada, edição concorrente, callback perdido, rollback e recuperação da reconciliação após interrupção durante uma chamada ao S3; a LLM foi simulada. Um proxy exclusivo do ensaio envelheceu as datas retornadas pela listagem e as tarefas no banco descartável foram envelhecidas, preservando a regra de 24 horas da aplicação. Foram verificados a remoção dos objetos, a retenção dos inventários e o evento de reconciliação concluída. A validação não cobre AWS S3 real nem a LLM real.

## Protocolo S3 simulado

A suíte Go completa passou com PostgreSQL em Docker, incluindo o cliente AWS SDK da API contra um endpoint HTTP simulado. O teste percorreu duas páginas, recebeu uma resposta de exclusão parcialmente malsucedida e retomou a limpeza preservando objetos recentes e referenciados. O simulador valida esse contrato específico, sem substituir um teste com AWS S3 real.

## Medição local da reconciliação

Com PostgreSQL em Docker e armazenamento simulado em memória, o cenário de 205 inventários sem jobs ou objetos listados passou de 820 consultas de referência e 205 chamadas de exclusão para 12 consultas e três chamadas após o agrupamento. As execuções medidas levaram 367 ms e 24 ms, respectivamente. São amostras locais isoladas, não estimativas de latência ou custo do AWS S3; a operação real ainda precisa ser medida.

## Pendente antes da ativação

- Executar o E2E estruturado opt-in (`tests/e2e/test_hybrid.py`) e ensaiar concorrência, callback incerto, limpeza e recuperação em ambiente controlado com S3 e configuração reais; avaliar custo e duração da varredura. Não havia bucket disponível para ensaio com S3 real.
- Validar coleta/agregação operacional e acordar metas de latência, custo, falhas, conflitos e qualidade visual com o responsável. As amostras aprovadas não incluem marca real.
- Ensaiar rollout e rollback no ambiente de destino, mantendo leitores e workers estruturados compatíveis. As flags de criação estruturada e reconciliação seguem desativadas por padrão.

O endpoint simulado não comprova compatibilidade integral com AWS S3, permissões, políticas do bucket, comportamento da rede ou qualidade de respostas da LLM em produção.

## Procedimento pendente para um bucket não produtivo

1. Identificar conta, região, bucket e credenciais já disponibilizadas ao ambiente de teste, sem registrá-las neste documento. Confirmar que a API e o worker acessam o mesmo bucket e que não há endpoint de simulador configurado inadvertidamente.
2. Em ambiente isolado, verificar as permissões necessárias para gravar, ler, listar e excluir objetos de teste. Implantar frontend, API e todos os workers compatíveis, com a reconciliação desativada inicialmente.
3. Executar o E2E opt-in documentado em `docs/TESTING.md`. Acrescentar ensaios com anexo de imagem, remoção da referência original, edições concorrentes e perda da resposta do callback; verificar histórico e downloads de versões anteriores.
4. Preparar artefatos descartáveis que atendam à janela mínima de 24 horas, ensaiar reconciliação, interrupção e nova execução, conferindo proteção de objetos referenciados e coleta de métricas. Não alterar timestamps ou reduzir a janela em um bucket compartilhado.
5. Medir duração, falhas, conflitos, custo e qualidade visual com uma marca real. Acordar as metas de expansão com o responsável antes de habilitar tráfego no ambiente de destino.
6. Ensaiar o rollback no ambiente de destino: desligar novas criações estruturadas e confirmar leitura, download e edição de versões existentes com workers compatíveis preservados.

Registrar resultados, período, versões implantadas e limitações; não incluir chaves, credenciais, URLs assinadas ou conteúdo privado.
