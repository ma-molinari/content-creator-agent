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

## Ensaio isolado com AWS S3 e LLM reais — 2026-11-22

- API, worker e PostgreSQL rodaram em containers Docker isolados; o bucket configurado foi acessado na região `us-east-2`. URLs assinadas geradas pela API e pelo worker foram baixadas com sucesso. O worker passou a assinar com SigV4 no endpoint regional resolvido pelo SDK; endpoints S3 customizados continuam suportados.
- O E2E estruturado opt-in passou com criação, edição, histórico e download de duas versões. Outro ensaio criou um post com anexo, confirmou a cópia do asset, removeu a origem de teste e editou a versão com sucesso. Duas edições concorrentes partiram da mesma versão: uma concluiu e a outra terminou em conflito. A LLM e o S3 foram reais; o conteúdo de perfil e a imagem eram sintéticos.
- Os chats e objetos do ensaio foram removidos; objetos dos prefixos dos jobs descartáveis foram conferidos e removidos antes do descarte do banco isolado. A rotina automática com objetos de mais de 24 horas não foi exercitada nesse ambiente.
- A imagem do worker foi reconstruída após incluir a biblioteca exigida pelo Playwright na imagem base. A suíte do worker passou com 198 testes e três ignorados; o ensaio Docker com LocalStack continuou passando.

## Callback incerto e preparação da reconciliação com S3 real — 2026-11-22

- Em stack Docker isolada, com S3 e LLM reais, o proxy de teste descartou a primeira resposta de conclusão após a API retornar sucesso. O worker repetiu o callback e foram verificadas exatamente uma versão para o job e uma resposta versionada no chat.
- Após excluir o chat descartável, um objeto de teste foi criado no prefixo do job e seu inventário foi mantido no volume Docker isolado `postmind-t18-real-s3_pgdata`. A verificação antecipada confirmou que a rotina não é habilitada antes da janela mínima.
- A partir de **2026-11-23 19:45:29 UTC** (16:45:29 em São Paulo), executar `python tests/docker_hybrid/real_s3.py verify`. O verificador confere o bucket e a região originais, cria objetos recente e referenciado, interrompe a API durante uma chamada real ao S3 e verifica a retomada, a remoção do objeto antigo e a preservação dos objetos recente e referenciado e do inventário. O ensaio real de 24 horas ainda não foi executado.
- Em 2026-11-23, o agregador foi executado sobre os logs preservados do ensaio: identificou um job estruturado concluído em 6.929 ms. É uma única amostra local, sem valor de meta ou validação do coletor operacional.
- A remoção do volume ou do objeto de teste antes da verificação invalida a preparação. As configurações de produção não foram alteradas. O proxy de interrupção foi validado separadamente com chamadas reais dos clientes Python e Go ao S3; o cenário completo de interrupção e proteção de referências depende da janela de 24 horas.

## Rollback em Docker com AWS S3 e LLM reais — 2026-11-23

- Em stack e banco descartáveis separados do ensaio de reconciliação, uma versão estruturada foi criada com S3 e LLM reais. Após desabilitar novas criações estruturadas e recriar a API, um novo chat usou o formato legado; leitura, download e edição do chat estruturado existente continuaram funcionando.
- Os objetos do ensaio e a stack descartável foram removidos. O teste não substitui o rollout e rollback no ambiente de destino nem a avaliação de qualidade com uma marca real.

## Protocolo S3 simulado

A suíte Go completa passou com PostgreSQL em Docker, incluindo o cliente AWS SDK da API contra um endpoint HTTP simulado. O teste percorreu duas páginas, recebeu uma resposta de exclusão parcialmente malsucedida e retomou a limpeza preservando objetos recentes e referenciados. O simulador valida esse contrato específico, sem substituir um teste com AWS S3 real.

## Medição local da reconciliação

Com PostgreSQL em Docker e armazenamento simulado em memória, o cenário de 205 inventários sem jobs ou objetos listados passou de 820 consultas de referência e 205 chamadas de exclusão para 12 consultas e três chamadas após o agrupamento. As execuções medidas levaram 367 ms e 24 ms, respectivamente. São amostras locais isoladas, não estimativas de latência ou custo do AWS S3; a operação real ainda precisa ser medida.

## Pendente antes da ativação

- Após a data indicada acima, executar a reconciliação preparada com S3 real, incluindo interrupção, recuperação e proteção de referências; avaliar custo e duração em escala representativa. O callback incerto e o E2E básico passaram com S3 e LLM reais no Docker isolado.
- Validar coleta/agregação operacional e acordar metas de latência, custo, falhas, conflitos e qualidade visual com o responsável. As amostras aprovadas não incluem marca real.
- Ensaiar rollout e rollback no ambiente de destino, mantendo leitores e workers estruturados compatíveis. As flags de criação estruturada e reconciliação seguem desativadas por padrão.

O endpoint simulado não comprova compatibilidade integral com AWS S3, permissões, políticas do bucket, comportamento da rede ou qualidade de respostas da LLM em produção.

## Procedimento pendente para um bucket não produtivo

1. Identificar conta, região, bucket e credenciais já disponibilizadas ao ambiente de teste, sem registrá-las neste documento. Confirmar que a API e o worker acessam o mesmo bucket e que não há endpoint de simulador configurado inadvertidamente.
2. Em ambiente isolado, verificar as permissões necessárias para gravar, ler, listar e excluir objetos de teste. Implantar frontend, API e todos os workers compatíveis, com a reconciliação desativada inicialmente.
3. O E2E opt-in, o anexo com remoção da origem, as edições concorrentes e a perda da resposta do callback passaram no Docker isolado com S3 e LLM reais; repetir os cenários conforme necessário no ambiente de destino e verificar histórico e downloads.
4. Preparar artefatos descartáveis que atendam à janela mínima de 24 horas, ensaiar reconciliação, interrupção e nova execução, conferindo proteção de objetos referenciados e coleta de métricas. Não alterar timestamps ou reduzir a janela em um bucket compartilhado.
5. Medir duração, falhas, conflitos, custo e qualidade visual com uma marca real. Acordar as metas de expansão com o responsável antes de habilitar tráfego no ambiente de destino.
6. Ensaiar o rollback no ambiente de destino: desligar novas criações estruturadas e confirmar leitura, download e edição de versões existentes com workers compatíveis preservados.

Registrar resultados, período, versões implantadas e limitações; não incluir chaves, credenciais, URLs assinadas ou conteúdo privado.
