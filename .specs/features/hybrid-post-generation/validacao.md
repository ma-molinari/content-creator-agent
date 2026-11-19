# Evidências de validação — geração híbrida

## Ambiente local

- Catálogo V1 aprovado pelo responsável em 2026-11-18, com amostras genéricas e fontes reais; não equivale a ensaio com marca real.
- Suíte Go unitária e integração completa com PostgreSQL temporário: passaram, incluindo concorrência, isolamento, rollback, callback com resposta perdida e recuperação de limpeza em processo separado.
- Integração API HTTP + worker HTTP + PostgreSQL e Chromium real: passou para criação, edição, imagem herdada após remoção da referência original e pedido de edição não suportado. LLM e S3 foram simulados.
- Worker: 197 testes passaram; dois testes opcionais de Chromium foram executados separadamente na validação anterior. Agregador local de métricas: dois testes passaram.
- Frontend: 17 testes e build passaram na validação anterior; não houve alterações no frontend nesta etapa.

## Ensaio Docker isolado

- API, worker e PostgreSQL executados em containers temporários; S3 foi simulado em memória com endpoint HTTP local, a LLM foi simulada e o Chromium usou uma fonte de teste. O E2E de criação, edição, histórico e downloads passou.
- Após reiniciar a API com a flag desligada, um novo chat foi criado no formato legado e um chat estruturado preexistente foi editado com sucesso.
- A rotina de reconciliação foi interrompida enquanto o S3 simulado estava pausado. Após reinício, removeu os dois objetos simulados pendentes, manteve os inventários e pôde ser executada novamente. A agregação dos logs da API identificou dois jobs estruturados concluídos; essa amostra não define metas.
- Containers, rede e arquivos temporários do ensaio foram removidos. O Docker Desktop foi iniciado e permaneceu disponível.

## Pendente antes da ativação

- Executar o E2E estruturado opt-in (`tests/e2e/test_hybrid.py`) e ensaiar concorrência, callback incerto, limpeza e recuperação em ambiente controlado com S3 e configuração reais; avaliar custo e duração da varredura. Não havia bucket disponível para ensaio com S3 real.
- Validar coleta/agregação operacional e acordar metas de latência, custo, falhas, conflitos e qualidade visual com o responsável. As amostras aprovadas não incluem marca real.
- Ensaiar rollout e rollback no ambiente de destino, mantendo leitores e workers estruturados compatíveis. As flags de criação estruturada e reconciliação seguem desativadas por padrão.

O endpoint simulado não comprova compatibilidade integral com AWS S3, permissões, políticas do bucket, comportamento da rede ou qualidade de respostas da LLM em produção.
