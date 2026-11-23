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
- A preparação determinou a elegibilidade após **2026-11-23 19:45:29 UTC** (16:45:29 em São Paulo). A verificação foi posteriormente executada, conforme o resultado abaixo.
- Em 2026-11-23, o agregador foi executado sobre os logs preservados do ensaio: identificou um job estruturado concluído em 6.929 ms. É uma única amostra local, sem valor de meta ou validação do coletor operacional.
- O volume e o objeto de teste foram preservados até a verificação. As configurações de produção não foram alteradas.

## Reconciliação interrompida com S3 real — 2026-11-23

Após a janela real de 24 horas, `python tests/docker_hybrid/real_s3.py verify`
passou na stack Docker isolada e no bucket configurado. A API foi interrompida
durante uma chamada ao S3 e reiniciada; a reconciliação removeu o objeto antigo e
preservou o objeto recente, o objeto com referência ativa e o inventário durável.
Os dois objetos e a referência temporária criados pelo verificador foram removidos
ao final. O volume isolado permanece preservado.

O ensaio usou as imagens locais já existentes, sem reconstrução: API
`sha256:f27ca364adac849f695c7c2707101db46dcd5c5efc32d5d508da81de1111db19`
e worker `sha256:6fab5787d4b37a2f7d48c3db5e0f7d251ea87da0186cf0c37f11e6a650788651`.
O commit exato dessas imagens não foi identificado; a evidência não substitui o
ensaio da versão implantada no ambiente de destino.

O agregador registrou duas execuções concluídas, nenhuma falha, dois inventários,
dois prefixos, duas páginas, seis objetos listados, 12 consultas de referência,
três chamadas de exclusão e oito tentativas de objeto; p95 de 1.209 ms. As
contagens somam execuções e tentativas, não objetos necessariamente distintos ou
requisições faturadas. A amostra não determina custo ou desempenho em escala.

## Rollback em Docker com AWS S3 e LLM reais — 2026-11-23

- Em stack e banco descartáveis separados do ensaio de reconciliação, uma versão estruturada foi criada com S3 e LLM reais. Após desabilitar novas criações estruturadas e recriar a API, um novo chat usou o formato legado; leitura, download e edição do chat estruturado existente continuaram funcionando.
- Os objetos do ensaio e a stack descartável foram removidos. O teste não substitui o rollout e rollback no ambiente de destino nem a avaliação de qualidade com uma marca real.

## Jornada pela interface com AWS S3 e LLM reais — 2026-11-23

- Em stack Docker isolada, o cadastro chegou à confirmação da chave de segurança. Na primeira tentativa, a aprovação automática recusou a confirmação porque não havia evidência de salvamento. Em nova conta descartável, o responsável salvou e confirmou a chave; a interface abriu a tela de login, e o login com a conta recém-criada passou, exibindo o bloqueio esperado até configurar o perfil.
- Com outra conta sintética criada pela API, passaram o login, o bloqueio antes de configurar o perfil, o preenchimento e salvamento de exemplos de marca e a liberação do chat.
- A interface criou e editou um post único e um carrossel de três slides; exibiu versões anterior e atual e listou ambos no histórico. O ZIP do carrossel continha três JPEGs de 1080×1350. Na edição, a comparação dos snapshots confirmou alteração apenas no conteúdo do título do primeiro slide; os demais slides permaneceram idênticos.
- API, worker, frontend e PostgreSQL rodaram em Docker com S3 e LLM reais. Os dados eram sintéticos e os objetos, o ZIP e a stack do teste foram removidos. A aprovação visual com marca real permanece pendente.
- Foi corrigido o proxy Nginx da SPA para aceitar endereço por ambiente: Docker Compose usa `api:8080` e a imagem mantém o padrão anterior do Railway. Os 17 testes do frontend e o build passaram.

## Referência visual de perfil com S3 e LLM reais — 2026-11-23

- Na stack de teste de cadastro, foi iniciada a API com o worker e uma conta sintética separada. Uma referência visual sintética foi enviada pela API de perfil, armazenada no S3 e recuperada por URL assinada.
- Um job de criação no formato legado executou o worker e a LLM reais. Instrumentação temporária limitada à solicitação sintética confirmou uma referência, resumo de visão não vazio e presença desse resumo no contexto enviado ao gerador. O post concluiu e a imagem foi recuperada com dimensões de 1080×1350.
- A referência e o chat sintéticos foram removidos; a instrumentação foi retirada e o worker normal permaneceu ativo. O teste comprova o caminho do contexto, não a reprodução exata da referência nem a utilização de uma marca real. O fluxo estruturado foi validado separadamente no ensaio abaixo.

## Referência visual no fluxo híbrido com S3 e LLM reais — 2026-11-23

- Em stack Docker isolada com `structured_v1` habilitado, uma conta e imagem sintéticas foram criadas. A referência foi enviada pela API de perfil, armazenada no S3 e recuperada por URL assinada.
- Instrumentação temporária restrita à solicitação de teste confirmou que o worker analisou a referência sem usar cache, produziu um resumo não vazio e incluiu esse resumo no payload efetivamente enviado à LLM de geração estruturada. A imagem também constava entre os assets autorizados.
- O job concluiu, com snapshot e manifesto estruturados no S3 e JPEG disponível em 1080×1350. O manifesto não continha imagens incorporadas neste ensaio: a referência foi usada como contexto textual, e o resultado não comprova reprodução visual exata.
- Chat, referência e objetos sintéticos foram removidos, assim como a stack descartável. O ambiente de teste do usuário e o volume reservado à reconciliação foram preservados.

## Ensaio comparativo de referências visuais — 2026-11-23

- Foram geradas duas amostras de controle e duas para cada uma de duas referências sintéticas, com mesmo pedido e textos de perfil. O fluxo híbrido usou S3 e LLM reais em Docker isolado.
- A referência roxa influenciou paleta e alinhamento nas duas amostras. Com a referência clara, fundo e texto azul ficaram próximos, mas o destaque laranja não foi usado. A composição e as barras das referências não foram reproduzidas.
- Comparativo visual, imagens, medições e limitações estão em `docs/avaliacoes/2026-11-23-referencias-visuais/README.md`. O ensaio não substitui validação com marca real ou define metas de qualidade.

## Protocolo S3 simulado

A suíte Go completa passou com PostgreSQL em Docker, incluindo o cliente AWS SDK da API contra um endpoint HTTP simulado. O teste percorreu duas páginas, recebeu uma resposta de exclusão parcialmente malsucedida e retomou a limpeza preservando objetos recentes e referenciados. O simulador valida esse contrato específico, sem substituir um teste com AWS S3 real.

## Medição local da reconciliação

Com PostgreSQL em Docker e armazenamento simulado em memória, o cenário de 205 inventários sem jobs ou objetos listados passou de 820 consultas de referência e 205 chamadas de exclusão para 12 consultas e três chamadas após o agrupamento. As execuções medidas levaram 367 ms e 24 ms, respectivamente. São amostras locais isoladas, não estimativas de latência ou custo do AWS S3; a operação real ainda precisa ser medida.

## Pendente antes da ativação

- Avaliar custo e duração da reconciliação em escala representativa. A execução
  isolada com S3 real, interrupção, recuperação e proteção de referências passou;
  o callback incerto e o E2E básico também passaram com S3 e LLM reais.
- Validar coleta/agregação operacional e acordar metas de latência, custo, falhas, conflitos e qualidade visual com o responsável. As amostras aprovadas não incluem marca real.
- Ensaiar rollout e rollback no ambiente de destino, mantendo leitores e workers estruturados compatíveis. As flags de criação estruturada e reconciliação seguem desativadas por padrão.

O endpoint simulado não comprova compatibilidade integral com AWS S3, permissões, políticas do bucket, comportamento da rede ou qualidade de respostas da LLM em produção.

## Procedimento pendente para um bucket não produtivo

1. Identificar conta, região, bucket e credenciais já disponibilizadas ao ambiente de teste, sem registrá-las neste documento. Confirmar que a API e o worker acessam o mesmo bucket e que não há endpoint de simulador configurado inadvertidamente.
2. Em ambiente isolado, verificar as permissões necessárias para gravar, ler, listar e excluir objetos de teste. Implantar frontend, API e todos os workers compatíveis, com a reconciliação desativada inicialmente.
3. O E2E opt-in, o anexo com remoção da origem, as edições concorrentes e a perda da resposta do callback passaram no Docker isolado com S3 e LLM reais; repetir os cenários conforme necessário no ambiente de destino e verificar histórico e downloads.
4. Repetir no ambiente de destino, se necessário, o ensaio de reconciliação com
   artefatos descartáveis elegíveis, interrupção e proteção de referências. Não
   alterar timestamps ou reduzir a janela em um bucket compartilhado.
5. Medir duração, falhas, conflitos, custo e qualidade visual com uma marca real. Acordar as metas de expansão com o responsável antes de habilitar tráfego no ambiente de destino.
6. Ensaiar o rollback no ambiente de destino: desligar novas criações estruturadas e confirmar leitura, download e edição de versões existentes com workers compatíveis preservados.

Registrar resultados, período, versões implantadas e limitações; não incluir chaves, credenciais, URLs assinadas ou conteúdo privado.
