# Proposta provisória — catálogo visual V2

**Estado:** proposta aprovada pelo responsável em 23/11/2026; ainda não implementada.
As [amostras](catalogo-v2-proposta.svg) mostram nove composições sintéticas na proporção
1080 × 1350. As medidas abaixo são coordenadas do canvas original; a imagem é uma
simulação, não uma saída do renderer e não comprova ausência de cortes no Chromium.

## Medidas propostas

As larguras são percentuais da área interna: `short` 25%, `medium` 50% e `full`
100%; espessuras `thin` 4 px, `medium` 12 px e `thick` 24 px. Uma barra
`rounded` tem raio de metade da espessura; `square` tem raio zero. Linhas usam
somente `square`. A decoração começa na borda esquerda da área interna, ocupa
espaço no fluxo e pode aparecer em qualquer posição da lista de elementos.
Mantêm-se os paddings e gaps dos layouts V1: hero 96/32 px, editorial 112/40 px,
quote 128/32 px. Limites: quatro decorações e 12 elementos por slide. Se a
composição exceder a área disponível, rejeitar antes de publicar sem apagar conteúdo.

## Comportamentos propostos

- **Contraste:** texto resolvido contra o fundo sólido com razão mínima 4,5:1,
  inclusive textos grandes. Rejeitar combinações insuficientes sem modificar
  silenciosamente o documento. Na promoção de V1, não alterar cor existente sem
  autorização; retornar erro recuperável caso o texto já não cumpra o limite.
  A mudança de token compartilhado deve validar todos os textos que o utilizam.
- **Referências conflitantes:** representar como incerto o que não puder ser
  conciliado; não declarar como observado nem inventar um destaque. Caso não seja
  possível produzir direção válida, falhar com pedido de nova tentativa. Falha
  parcial de leitura é falha da análise; edição comum não reanalisa referências.
- **Cache:** somente extração completa e válida; no máximo 128 entradas por
  processo e TTL de uma hora. Isolar por usuário e hash dos bytes ordenados e das
  versões de modelo, prompt e schema; incluir perfil caso influencie a extração.
  Não colocar conteúdo ou chaves legíveis nos logs.
- **Operações:** `set_palette_color` altera um token; `insert_decoration` insere no
  início ou após um elemento existente; `update_decoration` muda apenas campos
  especificados; `remove_decoration` remove o ID indicado. Os identificadores
  continuam únicos por slide. O conjunto é validado atomicamente.
- **Capacidade:** preservar `structuredPost.contractVersion: 1` para V1 e acrescentar
  listas explícitas de schemas lidos e escritos para V2. Um endpoint dedicado V2
  deve rejeitar workers antigos em vez de permitir downgrade silencioso; detalhes
  dos payloads e compatibilidade serão cobertos por fixtures antes de integração.

Exemplos provisórios de payload, sujeitos à validação formal e às regras de
autorização e preservação do TDD:

```json
{"op":"set_palette_color","token":"accent","color":"#F26930"}
{"op":"insert_decoration","slideId":"slide-1","afterElementId":null,"decoration":{"id":"bar-1","type":"decoration","kind":"bar","color":{"token":"accent"},"width":"full","thickness":"medium","corner":"rounded"}}
{"op":"update_decoration","slideId":"slide-1","elementId":"bar-1","changes":{"color":{"hex":"#12315D"}}}
{"op":"remove_decoration","slideId":"slide-1","elementId":"bar-1"}
```

`afterElementId: null` representa inserção no início; outro valor precisa existir
no mesmo slide. Em atualização, o conjunto final, inclusive a combinação de
`kind` e `corner`, é revalidado. Alterar token compartilhado pode afetar todos os
seus consumidores; o pedido deve autorizar esse efeito.

Exemplo provisório de `/capabilities`:

```json
{"structuredPost":{"contractVersion":1,"readSchemas":[1,2],"writeSchemas":[1,2],"decorationOperations":true}}
```

Para V2 a API verifica todos os destinos diretos elegíveis e usa esses mesmos
destinos no dispatch. A ausência dos campos novos anuncia somente V1; falhas de
sondagem não autorizam fallback. O endpoint dedicado sugerido é
`/jobs/structured/v2`.

Os limiares operacionais e a escolha de marca real autorizada continuam pendentes
para o aceite final; não são inferidos dessas amostras.
