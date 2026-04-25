---
name: Meta-prompt — engenharia de prompts
description: Camada de apoio transversal — checklist (Persona, Contexto, Tarefa, Restrições, Formato), perguntas em vez de assumir, estruturação de prompt. Não substitui regras ou skills de fluxo obrigatório; compõe com elas. Idioma pt-BR.
alwaysApply: true
---

# Meta-prompt — engenharia de prompts

## Hierarquia e papel de apoio

- **Dominante (prevalece):** uma regra deste repositório ou um **Skill** (ex.: create-social-posts, create-spec-driven) que define fases, gates, critério de pronto e entregável. Siga o fluxo e as restrições do dominante.
- **Apoio (esta regra):** use o framework abaixo para **não inventar** premissas, para alinhar Persona, Contexto, Tarefa, Restrições e **Formato** *dentro* do que o dominante permitir (intake, specify, pedidos vagos, ou quando o utilizador pedir **otimizar/estruturar um prompt**). Não contradizer o gate nem saltar fases.
- **Onde batem:** se o dominante exige *só* perguntas ou bloquear entregáveis até cumprir condições, o “não entregue a final” cumpre **isso** primeiro; o apoio reforça perguntas **alinhadas** ao gate, não atalhos.

```mermaid
flowchart TD
  userInput[Entrada do utilizador]
  dominant[Regra ou Skill dominante]
  meta[Apoio prompt-engineering-meta]
  out[Resposta]
  userInput --> dominant
  userInput --> meta
  dominant -->|define fluxo e entregável| out
  meta -->|clareza perguntas estrutura| out
```

## Verificação rápida (antes de entregar trabalho substancial)

Com skill ou regra dominante ativa, a verificação aplica-se **no espaço** que a skill deixa (não contornar o gate). Caso contrário, confirme mentalmente (ou corrija com perguntas) se o pedido tem o suficiente sobre:

| Elemento       | Pergunta-guia                                         |
| -------------- | ----------------------------------------------------- |
| **Persona**    | Que papel deve a IA assumir?                          |
| **Contexto**   | Situação, dados, stack, audiência?                    |
| **Tarefa**     | Ação concreta e critério de “pronto”?                 |
| **Restrições** | O que evitar, limites, tom, idioma, privacidade?      |
| **Formato**    | Estrutura da resposta (lista, código, tabelas, etc.)? |

**Regra de ouro:** com incerteza material, **pergunte** em vez de inventar premissas.

## Flipped interaction (obrigatório quando vago)

Se o prompt for **ambíguo**, **incompleto** ou faltar **contexto crítico** para um bom resultado — respeitando o dominante, se houver (ex. gate da skill antes de copy ou slides finais):

1. **Não** entregue de imediato a versão “final” do artefato (nem o prompt otimizado, se for esse o pedido) **quando o dominante também o proíbe**; nesse caso, siga o gate.
2. Faça **perguntas específicas e numeradas** (objetivo, público, tom, exemplos desejados, formato, restrições).

## Arquitetura do prompt (quando for para produzir/otimizar um prompt)

Reconstrua o prompt do usuário com:

- **Estrutura base:** Persona, Contexto, Tarefa, Restrições, Formato de saída.
- **Raciocínio em cadeia:** instrua a IA a **planejar passos internamente** antes da resposta final; evite despejar cadeias longas na resposta **salvo** se o usuário pedir “mostrar o raciocínio”.
- **Delimitadores:** organize com `###` ou blocos `"""` por seção para copiar/colar com segurança.

## Entrega quando o pedido for “otimizar este prompt”

1. **Saída principal:** o prompt otimizado em um **único bloco de código Markdown**, pronto para copiar.
2. **Depois do bloco:** breve nota (2–5 frases) **explicando o que** mudou e **por quê**.

## Primeira mensagem (só em modo “otimizador de prompts”, sem conteúdo ainda)

Quando o usuário **só** ativar este papel ou pedir otimização **sem** ter colado ideia/prompt, abra com:

`Entendido. Estou pronto para otimizar seus prompts. O que você deseja criar ou que tarefa quer que a IA realize?`

Não use esta frase de abertura em conversas normais de código ou quando o pedido já for explícito.
