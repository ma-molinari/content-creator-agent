# Validação de fidelidade visual V2

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

- Ensaio comparativo com LLM e S3 reais para V2, referências ambíguas e carrossel;
  marca real autorizada e revisão humana de fidelidade/legibilidade.
- Definir metas operacionais e de qualidade com o responsável a partir das medições;
  exercitar coleta, rollout e rollback no ambiente de destino.
- Concluir T18 híbrida: a reconciliação com S3 real preparada no volume
  `postmind-t18-real-s3_pgdata` fica elegível em 23/11/2026 após 16h45:29 BRT.
  Não remover esse volume antes da verificação.
- Não habilitar `STRUCTURED_VISUAL_V2_ENABLED` em tráfego antes da conclusão dos
  gates acima. Os resultados com LocalStack não demonstram fidelidade de LLM real.
