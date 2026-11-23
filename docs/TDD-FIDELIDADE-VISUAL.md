# TDD — Fidelidade visual: paleta, barras e linhas

| Campo | Valor |
| --- | --- |
| Responsável técnico | Responsável pelo projeto |
| Equipe | Responsável pelo projeto |
| Ticket | Não há |
| Status | Proposta para revisão |
| Data | 2026-11-23 |
| Prazo | Não definido |
| Dependência | Geração híbrida e sua aceitação operacional, especialmente T18 |

## 1. Contexto e problema

O fluxo híbrido salva cada versão como snapshot JSON imutável no S3, gera HTML/JPEG e registra no PostgreSQL o schema, o renderizador, o job e a versão anterior. Referências visuais do perfil são analisadas por um modelo de visão; o resumo textual é usado como contexto na criação.

O [ensaio comparativo](avaliacoes/2026-11-23-referencias-visuais/README.md) gerou dois controles e duas amostras para cada uma de duas referências sintéticas. A referência roxa influenciou cor e alinhamento; a clara aproximou fundo e texto azul, mas omitiu o acento laranja. Nenhuma amostra reproduziu as barras. O conjunto é pequeno e não comprova taxa de fidelidade.

Uma causa estrutural verificável é que o documento atual só aceita texto e imagem, fundos sólidos e três layouts. Não há elementos para barras ou linhas, nem uma paleta estruturada no snapshot. O resumo visual é texto livre; a informação pode ser omitida ou interpretada de maneira inconsistente.

**Objetivo:** permitir que o fluxo híbrido represente paleta, barras e linhas de maneira controlada, editável e versionada, e verificar seu uso nas imagens entregues. A proposta busca aproximar a identidade visual, sem prometer cópia exata da referência.

## 2. Escopo

**Incluído:**

- Direção visual estruturada derivada das referências autorizadas, com cores e indicações de barras/linhas quando identificáveis.
- Documento `schemaVersion: 2` com paleta e elementos gráficos simples; renderização controlada e operações de edição tipadas.
- Criação V2 e edição linear de versões V1/V2, preservando histórico, concorrência e artefatos existentes.
- Validação equivalente em Go e Python, negociação de capacidades, rollout, observabilidade, segurança e ensaios comparativos.

**Fora de escopo:**

- Editor de arrastar e soltar, controle pixel a pixel, formas livres, ícones, stickers, gradientes, texturas, animações e fontes arbitrárias.
- Extração ou reprodução automática de logotipos, texto literal, pessoas ou imagens de terceiros.
- Conversão automática de HTML legado, edição de versões históricas, ramificações ou merge.
- Garantia de equivalência perceptual perfeita ou definição unilateral de metas de negócio.

## 3. Estado atual relevante

- O formato de chat e job é `legacy_html` ou `structured_v1`. Esse discriminador define a rota de processamento; **não é o mesmo campo que `schemaVersion` do snapshot**.
- O worker valida `PostDocumentV1` com `extra="forbid"`; os elementos são texto/imagem, e o limite atual é 20 slides, 12 elementos por slide e 2 MiB por documento. A edição suporta operações de texto, fundo, estilo, imagem e layout, sem inclusão/exclusão de elementos.
- A API valida novamente o documento V1, exige `schemaVersion == 1` no callback e verifica imagens autorizadas, manifesto, ownership e prefixo do job. O callback publica a versão transacionalmente após comparar a base esperada com a corrente.
- `/capabilities` informa `structuredPost.contractVersion: 1`; a API atual exige igualdade com `1` e consulta todos os destinos diretos antes de despachar. Esse sinal, sozinho, **não comprova suporte ao schema V2**.
- O renderer V1 salva o HTML e o JPEG efetivamente entregues. Sua correção de contraste pode alterar o HTML renderizado sem alterar o snapshot; medições do snapshot, portanto, não são prova do contraste efetivo do JPEG.
- `STRUCTURED_POSTS_ENABLED` controla a escolha de formato na criação de **novos chats**; desligá-la não converte os estruturados existentes em legados.

## 4. Decisões e invariantes

1. **Contrato aditivo por versão:** introduzir `schemaVersion: 2`, com validador e renderer próprios. Manter `postFormat: structured_v1` como identificador existente da família de processamento, evitando uma mudança implícita no enum persistido; o número do schema segue no snapshot e em `post_versions`.
2. **Edição linear:** editar somente a versão corrente; o job registra a base esperada e o callback rejeita conflito. Uma criação explícita em chat existente continua gerando uma raiz, sujeita à comparação da versão corrente.
3. **V1 → V2:** quando a escrita V2 estiver habilitada, a primeira edição de uma base V1 promove uma cópia em memória para V2 e publica uma nova versão V2 se o job terminar com sucesso. A base V1 e seus arquivos nunca são reescritos. Sem a flag, edições de base V1 continuam produzindo V1.
4. **V2 existente após rollback:** desligar a flag impede novas criações V2 e novas promoções V1→V2, mas mantém edição de uma base já V2 por worker capaz de ler e escrever V2. Se a capacidade faltar, bloquear a mutação com mensagem clara; preservar leitura e download. A flag controla a escolha do schema, não impede novas decorações em edições V2. Se for necessário suspender essas operações por segurança, bloquear mutações V2 explicitamente e manter leitura/download; não fazer downgrade.
5. **Preservação semântica:** operações alteram apenas os campos ou elementos selecionados. Alterações de um token de paleta afetam todos os campos que referenciam esse token; só são aceitas quando esse efeito coletivo corresponde ao pedido. Uma alteração local usa cor literal ou operação direcionada.
6. **Fonte canônica e segurança:** o snapshot guarda os valores finais e a intenção gráfica. Não aceitar HTML, CSS, URLs arbitrárias, scripts ou coordenadas livres fornecidos pela LLM. HTML/JPEG de versões anteriores continuam sendo o registro visual entregue.
7. **Sem migração em massa:** não há backfill nem substituição de artefatos V1 ou legados. A promoção V1→V2 é determinística e acontece apenas em memória no job de edição.

## 5. Contrato proposto

### 5.1 Direção visual e paleta

A análise das referências produz uma **direção visual estruturada temporária**, sujeita a schema fechado: cores aproximadas para `background`, `text` e `accent`; indicação de ausência/ambiguidade; e uma lista limitada de barras ou linhas identificadas com posição semântica. Cada indicação é classificada como observada ou incerta. Essa classificação é uma saída do modelo, não uma confiança estatística calibrada.

A imagem segue como referência de estilo; não é obrigatório incorporá-la ao slide. O gerador recebe a direção validada e o perfil, além do pedido e dos IDs autorizados. A paleta efetivamente escolhida vai para o snapshot V2. **Não persistir automaticamente o texto integral extraído da referência**, URLs assinadas ou imagem em logs; a retenção de imagens segue o fluxo de assets autorizado existente.

Quando não houver referências, o gerador poderá escolher cores válidas a partir do perfil e do pedido. Na criação V2 com referências, ou numa edição que peça explicitamente para aplicá-las, se elas não puderem ser analisadas ou a saída permanecer inválida após retentativa limitada, falhar o job com mensagem de nova tentativa; não apresentar como sucesso uma geração que silenciosamente ignorou as referências. Numa edição comum que não peça reaplicar referências, usar a paleta e os elementos do snapshot base; a indisponibilidade de uma referência original não deve impedir uma edição de texto. Ausência/ambiguidade de um detalhe específico não autoriza inventá-lo como observado.

O cache atual da análise é indexado pelas chaves das imagens, mas o resumo usa também AUDIT/BRAND. Para V2, separar a extração visual independente do perfil da etapa que combina instruções ou invalidar o cache quando qualquer entrada relevante mudar. A chave deve incluir identidade/versão imutável das imagens, versão do prompt/modelo e isolamento por usuário; falhas e saídas incompletas não devem ser cacheadas como sucesso. Limitar retenção e tamanho do cache.

### 5.2 Documento V2

Os exemplos abaixo ilustram o contrato a ser formalizado em schemas compartilhados e fixtures de paridade; campos e aliases são normativos para a implementação desta proposta.

```json
{
  "schemaVersion": 2,
  "postType": "single",
  "palette": { "background": "#FFF5E9", "text": "#12315D", "accent": "#F26930" },
  "slides": [{
    "id": "slide-1",
    "layout": "editorial",
    "background": { "type": "solid", "color": { "token": "background" } },
    "elements": [
      { "id": "bar-1", "type": "decoration", "kind": "bar", "color": { "token": "accent" }, "width": "full", "thickness": "medium", "corner": "rounded" },
      { "id": "title", "type": "text", "role": "heading", "content": "Uma pausa faz diferença", "style": { "color": { "token": "text" }, "size": "large", "font": "inter", "weight": "bold", "alignment": "center" } }
    ]
  }]
}
```

- A paleta V2 contém os três papéis acima, cada um com hexadecimal RGB de seis dígitos. Uma cor usada por fundo, texto ou decoração é exatamente uma referência `{ "token": "background|text|accent" }` ou um literal `{ "hex": "#RRGGBB" }`; rejeitar objetos ambíguos, tokens ausentes e campos extras.
- `decoration.kind` admite `bar` ou `line`, somente horizontais. `width`: `short`, `medium` ou `full`; `thickness`: `thin`, `medium` ou `thick`; `corner`: `square` ou `rounded`, sendo `line` apenas `square`. As combinações correspondem a medidas fixas do renderer, não a CSS livre.
- A ordem em `elements` define a posição no fluxo do layout. Barras e linhas ocupam espaço e não podem sobrepor texto; sem z-index, posição absoluta, conteúdo textual ou URL. São permitidas no máximo quatro decorações por slide, dentro do limite total de 12 elementos. Manter os demais limites V1; validar IDs únicos, tipos, dimensões de canvas, quantidade e autorização dos assets.
- Os layouts continuam `hero`, `editorial` e `quote`; as opções atuais de texto e imagem permanecem. A paleta é uma orientação explícita: literais são permitidos para preservar versões promovidas e exceções justificadas.
- Ao converter V1, copiar IDs, ordem, textos, cores, fontes, layout e assets; representar cada cor V1 como literal V2. Inicializar os três tokens de forma determinística a partir das cores disponíveis, mas não vincular automaticamente os elementos existentes a eles. A conversão não acrescenta barras nem altera o original.

### 5.3 Edição

Ampliar o contrato de operações para permitir: definir um token da paleta; inserir uma decoração no início ou após um ID existente; alterar cor, largura, espessura, cantos ou tipo de uma decoração; e removê-la. Os nomes e payloads exatos das operações devem constar das fixtures versionadas antes da implementação do planner. IDs são gerados/validados pelo sistema, únicos por slide e preservados enquanto o elemento existir.

O planner recebe a versão de schema alvo e emite somente operações compatíveis. Numa edição que solicite aplicar as referências atuais, também recebe a direção visual validada; numa edição comum, usa o snapshot da base e não reaplica implicitamente o perfil ou as referências atuais. O aplicador valida o conjunto inteiro, a existência e tipo dos alvos, a ordem de inserção, a autorização de imagens, os limites e o documento final. Em falha, nenhuma operação é publicada. Pedidos não representáveis continuam retornando mensagem de reformulação; não há fallback silencioso para HTML legado.

Exemplos de comportamento:

- “Adicionar uma barra laranja no topo”: inserir uma barra no início, vinculada ao token `accent` quando isso corresponder à paleta definida.
- “Mudar somente esta linha para azul”: alterar apenas a cor dessa linha, sem atualizar o token compartilhado.
- “Mudar a cor de destaque do post”: atualizar o token `accent` somente se o efeito em todos os seus consumidores estiver de acordo com o pedido.

### 5.4 Renderização e validação visual

O renderer V2 resolve tokens antes de gerar HTML/CSS controlado e registra sua própria versão. Validar segurança, fontes, assets, limites e ausência de cortes. Definir e documentar valores fixos de largura, espessura, cantos e espaçamento por enum antes de congelar o catálogo; usar fixtures visuais 1080×1350 com fontes fixadas.

Para V2, o controle de contraste deve ser explícito e verificável: validar as cores resolvidas e, se for necessário corrigi-las, aplicar a decisão ao documento antes de persistir ou falhar com erro recuperável. Não modificar silenciosamente somente o HTML/JPEG de uma forma que contradiga o snapshot. Definir limiares e política de correção com o responsável. V1 mantém seu comportamento atual; os arquivos V1 históricos não são reprocessados.

## 6. Fluxos e contratos entre serviços

### Criação

1. A API determina o formato do chat conforme o comportamento existente e, para job estruturado, decide e persiste o schema alvo antes do dispatch.
2. Com a flag V2 desligada, novas raízes estruturadas usam V1. Com ela ligada e capacidade confirmada, usam V2. A flag V2 não habilita, por si só, novos chats estruturados.
3. O worker obtém as referências autorizadas, extrai e valida a direção visual, gera documento V2, valida, renderiza e envia snapshot, manifesto e imagens imutáveis ao prefixo do job.
4. O callback informa schema e renderer efetivos. A API compara o schema com o alvo persistido no job, valida o documento correspondente e publica somente após as verificações transacionais e de base.

### Edição

1. A API verifica ownership, cliente compatível, base corrente e capacidade de leitura/escrita exigida. Registra `baseVersionId` e schema alvo; a versão alvo é decidida no aceite, não pelo callback.
2. Para base V1, aplica a política da seção 4. Para base V2, o alvo é V2 mesmo com a flag de novas escritas desligada.
3. O worker lê o snapshot exato, promove V1 em memória se necessário, planeja e aplica operações, renderiza e envia artefatos a um novo prefixo do job. Analisa as referências atuais para a edição apenas quando o pedido exigir reaplicá-las; a indisponibilidade delas não bloqueia alterações independentes no snapshot.
4. Na conclusão, a API valida documento, assets, alvo e base dentro do fluxo existente. Se a base mudou, retorna conflito e não move o ponteiro corrente. Timeout ou resposta incerta do callback continua sujeito a retentativa idempotente e reconciliação segura.

### Negociação e dados duráveis

Estender `/capabilities` **de forma aditiva**, preservando `structuredPost.contractVersion: 1` para chamadas existentes. Uma resposta nova deve anunciar separadamente os schemas que lê e escreve e a capacidade de operações gráficas. Ausência dos novos campos significa apenas suporte V1. Antes de criar job V2, a API deve verificar todos os destinos diretos elegíveis e usar os mesmos destinos verificados no dispatch; incompatibilidade ou disponibilidade desconhecida bloqueia a mutação V2, sem fallback silencioso.

Persistir no job o schema alvo e, para edição, a base já armazenada. A migração deve ser aditiva e tratar jobs estruturados anteriores ou em voo sem campo alvo como V1, inclusive em callbacks tardios; jobs legados não precisam de alvo estruturado. Não alterar o snapshot ou os registros existentes. Definir no contrato como o alvo é transmitido ao worker e validá-lo no endpoint de dispatch; um worker V1 não deve aceitar silenciosamente um job destinado a V2.

A API não pode aceitar V2 até que todas as suas réplicas capazes de receber callbacks e todos os workers elegíveis tenham sido atualizados. Ampliar o validador Go e o upload/callback Python, que hoje estão explicitamente fixados em V1. A mudança deve cobrir parsing, limites, versão do renderer, comparação com alvo/base, manifesto e tipos de conteúdo. `post_versions.schema_version` e `renderer_version` já existem, mas as validações atuais precisam ser estendidas.

O frontend continua exibindo JPEGs e histórico sem interpretar o snapshot. Preservar o contrato atual de cliente e verificar em testes que clientes compatíveis não perdem leitura ou edição; qualquer nova interface explícita para paleta ou formas é posterior. Novos erros de capacidade, incompatibilidade ou referência precisam ser apresentados em português sem expor conteúdo privado.

## 7. Compatibilidade e rollout

| Base/fluxo | Flag V2 desligada | Flag V2 ligada e capacidade confirmada |
| --- | --- | --- |
| HTML legado | Mantém leitura e edição legadas | Mantém leitura e edição legadas |
| Criação estruturada | V1, sujeito às regras existentes de chat | V2 |
| Edição de base V1 | Nova versão V1 | Promoção em memória e nova versão V2 |
| Edição de base V2 | Nova versão V2; exige capacidade V2 | Nova versão V2; exige capacidade V2 |

1. Entregar schemas/fixtures e suporte de leitura V1/V2, validação de API, renderer e operações; manter escrita V2 desligada.
2. Implantar e verificar capacidade de **todas** as réplicas de API e dos destinos diretos de worker, inclusive callbacks e jobs em voo. Monitorar incompatibilidades.
3. Ensaiar criação e edição V2 e promoção V1→V2 em ambiente não produtivo, com S3 real; comparar imagens e histórico. Manter a aceitação operacional da T18 como pré-requisito para tráfego estruturado.
4. Habilitar escrita V2 gradualmente somente após aceite visual e operacional. Se houver divergências ou falhas relevantes, desligar a flag, drenar jobs e investigar; não excluir nem reverter migrations/snapshots.
5. Preservar leitores e workers capazes de tratar V2 já publicado. O retorno a binários apenas V1 é inseguro enquanto houver V2: manter compatibilidade ou bloquear edição de V2 e oferecer leitura/download. Nunca rebaixar V2 silenciosamente para V1.

## 8. Segurança e privacidade

- O worker recebe apenas fontes autorizadas pela API; IDs de imagem são resolvidos por ownership, sem aceitar chaves S3/URLs inventadas pela LLM. A direção visual não concede acesso adicional a assets.
- Submeter cores, tokens, IDs, enums, limites, tipos e operações a validação estrita no worker e na API; escapar textos e manter bloqueio de rede do navegador, exceto recursos explicitamente autorizados.
- Limitar tamanho e quantidade de referências, saída da visão, elementos, operações e retentativas. Preservar as validações de arquivo, prefixo, manifesto, limpeza e reconciliação existentes.
- Não registrar imagens, texto de marca, resumos, prompts, URLs assinadas ou credenciais em logs/métricas. Chaves de cache não devem conter conteúdo legível; observar isolamento por usuário.

## 9. Testes e critérios de aceite

### Contrato e renderização

- Fixtures compartilhadas Go/Python aceitam V1 e V2 válidos e rejeitam campos extras, tokens desconhecidos, cores inválidas, IDs duplicados, elementos ou decorações acima dos limites e assets não autorizados.
- Promoção V1→V2 preserva os campos semânticos e não altera a origem; fixtures demonstram equivalência visual controlada para documentos sem novos elementos. Arquivos históricos continuam iguais byte a byte; **não se promete igualdade de pixels em toda nova renderização**.
- Renderer V2 cobre barra e linha em cada enum, ordem, dimensões, safe area, contraste conforme política aprovada e ausência de overflow. Verificar o HTML/JPEG efetivo e a consistência com o snapshot.

### Criação, edição e compatibilidade

- Criar com e sem referência, com paleta válida, barra/linha e rejeição explícita de referência indisponível ou saída inválida. Verificar que a direção visual observada chega ao gerador, sem vazar conteúdo nos logs.
- Editar cada propriedade, inserir e remover decoração, alterar token compartilhado e cor local; testar preservação dos elementos não envolvidos, transação atômica e pedido não representável. Com a referência original indisponível, uma edição textual comum deve funcionar; uma edição que peça reaplicá-la deve falhar claramente.
- Cobrir V1→V2, V2→V2, V1 com flag desligada, nova raiz, bases obsoletas, duas edições concorrentes, callback repetido/resposta perdida, falha de upload e worker incompatível.
- Testar negociação mista, API antiga/nova, flags desligadas, jobs V1 em voo durante a migração, leitura/download de V1/V2/legado e rollback com V2 já publicado.

### Avaliação visual e operacional

- Reexecutar o [ensaio comparativo](avaliacoes/2026-11-23-referencias-visuais/README.md) com controles, as referências sintéticas originais e amostras suficientes para avaliação. Para uma direção visual validada que especifique uma barra no topo, uma fixture determinística deve produzir a barra na posição e cor resolvida esperadas; uma referência sem esse destaque não deve obrigatoriamente gerá-lo.
- Incluir carrossel, referências ambíguas e pelo menos uma marca real autorizada. Comparar paleta, alinhamento, presença dos destaques, composição e legibilidade; registrar imagens, metodologia e revisão humana.
- Definir com o responsável limiares de fidelidade, latência, custo e falhas antes de habilitar tráfego. Não inferir aprovação estatística a partir das duas amostras anteriores.

## 10. Monitoramento e riscos

Emitir apenas eventos agregáveis sem conteúdo com schema/renderer, etapa de extração/validação/renderização, resultado, motivo categorizado, duração e quantidades de decorações; contar conflitos e indisponibilidade de capacidade. Medir uso e custo adicional de visão/geração e distinguir falha de extração, schema, contraste, overflow e publicação. Agregação operacional e seus limiares precisam ser validados no ambiente de destino.

| Risco | Mitigação |
| --- | --- |
| Modelo identifica cor ou barra incorretamente | Schema fechado, estado incerto, testes com referências ambíguas e revisão visual; não tratar confiança como garantia. |
| Schema V2 aceito por algumas réplicas e rejeitado por outras | Implantação compatível antes da flag, capacidade por destino, alvo persistido no job e teste de callbacks em voo. |
| Mudança de paleta altera elementos não pretendidos | Tokens explícitos, literais para exceções e testes de operações; promoção V1 preserva cores literais. |
| V2 publicado deixa de ser editável após rollback | Manter leitores/escritores V2; na ausência, bloquear edição e preservar leitura/download. |
| Formas causam corte, contraste ruim ou diferenças do snapshot | Limites e fluxo controlado; validação pós-renderização e política explícita de contraste antes da publicação. |
| Referência ou resumo indevidamente compartilhado por cache | Isolamento por usuário, chave versionada por entradas, retenção limitada e nenhum conteúdo sensível em logs. |
| Custos/latência maiores e excesso de retentativas | Limites, cache seguro, medição e metas definidas antes de expandir tráfego. |

## 11. Plano de implementação

1. Fechar exemplos de barras/linhas, medidas do catálogo, política de contraste e fixtures de paridade V1/V2; validar visualmente com o responsável.
2. Implementar contratos, promoção determinística e testes de operações; manter escrita V2 desativada.
3. Implementar renderer V2, validações no worker e testes de imagem/snapshot.
4. Adicionar direção visual estruturada, cache seguro e integração com criação/edição.
5. Ampliar validação da API, schema alvo do job e negociação de capacidades, incluindo jobs e callbacks V1 em voo.
6. Executar ensaios de integração, concorrência, segurança, histórico, rollback e comparação com/sem referência; atualizar documentação operacional.
7. Depois de concluir T18 e obter aceite visual e operacional, ativar gradualmente e monitorar.

## 12. Questões pendentes para aprovação

- Quais tamanhos, espaçamentos e combinações de barras/linhas entram no catálogo V2 após a revisão visual?
- Quais limiares de contraste e como tratar conflitos entre fidelidade e legibilidade?
- Como resolver referências com paletas ou estruturas conflitantes e quando informar o usuário que um detalhe não é suportado?
- Quais amostras de marca real e metas de fidelidade, latência, custo e falha serão usadas no aceite?
- Qual política de expiração e limite do cache é adequada para o ambiente de produção?
