# Validação de fidelidade visual V2

## Política de referências — 23/11/2026

- O ensaio em Docker com LocalStack verificou criação sem incorporar a referência,
  inclusão por solicitação explícita e preservação da imagem incorporada após a
  remoção da referência original e uma edição posterior. A LLM foi simulada.
- Com S3 e OpenAI reais, uma referência autorizada e carrossel estruturado,
  os mesmos três cenários passaram; o histórico anterior também foi preservado.
  As imagens e resultados do ensaio permanecem locais.
- Em tentativas anteriores, a classificação de reaplicação foi acionada em uma
  edição apenas textual e a extração visual retornou uma combinação inválida de
  estado e cor. O primeiro caso foi corrigido e o prompt do segundo foi reforçado;
  saídas inválidas continuam sendo rejeitadas, e a robustez da extração depende
  do modelo. Estes testes não constituem aprovação da fidelidade visual.

## Integração — 23/11/2026

- Suíte Go unitária e integração PostgreSQL completas; seleção transacional V1/V2,
  migração de jobs antigos, callbacks idempotentes e concorrência também têm casos
  específicos. O PostgreSQL de integração foi descartável.
- Worker: 270 testes passaram e quatro testes opcionais ficaram ignorados na suíte
  geral. Além disso, 46 testes do renderer rodaram com Chromium e fonte local; 14
  testes cobriram upload parcial e autorização de assets, incluindo V2.
- `HYBRID_DOCKER_S3=localstack python tests/docker_hybrid/run.py` passou em stack
  descartável com API e worker reais, PostgreSQL e LocalStack. A LLM, a decisão de
  reaplicar referências, a análise de anexos e a geração legada foram simuladas;
  renderização Chromium, upload, callback, banco e API foram reais.
- O ensaio cobre criação V1, promoção V1→V2, edição V2, referência registrada cujo
  objeto foi removido (edição textual passa e reaplicação falha), duas edições V2
  concorrentes, nova raiz V2, edição V2 após rollback da flag, bloqueio ao simular
  worker somente V1, nova raiz V1, histórico/download V1/V2/legado, callback com
  resposta perdida e reconciliação com S3 simulado. A versão anterior e seus assets
  herdados permaneceram utilizáveis após remoção da origem do anexo.
- As garantias de origem vêm do dispatch e da validação do worker; igualdade entre
  IDs e manifesto no callback não é prova independente da origem dos bytes.

## Pendente para aceite e ativação

A instrumentação parcial da T14 agrega eventos V2 com lista fechada de resultados
e motivos. Três testes de agregação e 42 testes do worker/Chromium passaram; o
ensaio Docker com LocalStack também verificou emissão e agregação de extração,
validação, renderização e publicação. A coleta e o custo permanecem por validar
no ambiente de destino; isso não constitui aceite operacional.

- Ensaio sintético com LLM e S3 reais, inclusive carrossel com referências
  conflitantes, registrado em `docs/avaliacoes/2026-11-23-fidelidade-v2/`.
  Permanecem pendentes revisão humana de fidelidade, legibilidade e incorporação
  de referências como imagens.
- Duas referências fornecidas pelo usuário foram usadas com autorização em quatro
  carrosséis: controle, cada imagem separada e ambas. Resultados e limitações em
  `docs/avaliacoes/2026-11-23-fidelidade-v2/referencias-fornecidas.md`; originais e
  imagens geradas permanecem locais e não são publicados no repositório.
- O responsável não aprovou a fidelidade visual e definiu que referências são
  apenas orientação, salvo pedido explícito para incluí-las. A política foi
  implementada para o fluxo estruturado V1/V2 com seleção explícita, validação
  posterior e preservação de imagens herdadas; os demais limites de composição e
  o aceite visual continuam pendentes.
- Definir metas operacionais e de qualidade com o responsável a partir das medições;
  exercitar coleta, rollout e rollback no ambiente de destino.
- Concluir aceite operacional da T18 híbrida. A reconciliação com S3 real passou
  após a janela de 24 horas, com interrupção e proteção de referências; falta
  validar coleta, metas e operação no destino.
- Não habilitar `STRUCTURED_VISUAL_V2_ENABLED` em tráfego antes da conclusão dos
  gates acima. Os resultados com LocalStack não demonstram fidelidade de LLM real.
