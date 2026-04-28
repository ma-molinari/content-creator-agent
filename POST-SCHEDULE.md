# Plano mensal de conteúdo: @molistack.dev

**Frequência recomendada:** 3 postagens por semana (segunda, quarta e sexta).

**Objetivo:** Atrair desde juniores (pela base sólida) até seniores (pela eficiência e detalhes técnicos).

---

## Semana 1: A base oculta (low-level e memória)

*Foco em como as coisas funcionam por baixo do capô.*

| Dia    | Tópico                       | Conteúdo sugerido para o carrossel                                                                 |
| ------ | ---------------------------- | -------------------------------------------------------------------------------------------------- |
| Post 1 | Tipos primitivos e memória   | Além de `string`/`int`: stack vs heap de forma visual; como a alocação impacta a performance.     |
| Post 2 | Lógica além do if/else       | Curto-circuito (`&&`, `||`); operador ternário; quando simplificar condicionais.                  |
| Post 3 | Arrays vs lists              | Diferença física na memória; complexidade O(n) para busca e inserção; quando escolher cada um.      |

---

## Semana 2: Fluxo e estruturas de dados

*Foco em algoritmos eficientes e organização de dados.*

| Dia    | Tópico                     | Conteúdo sugerido para o carrossel                                                                 |
| ------ | -------------------------- | -------------------------------------------------------------------------------------------------- |
| Post 4 | Loops de alta performance  | Comparativo: `for` tradicional vs `foreach` vs `map`; qual é mais rápido em grandes volumes?          |
| Post 5 | Recursão vs iteração       | O que é stack overflow na prática; quando a recursão é elegante (ex.: percorrer árvores).           |
| Post 6 | Dicionários e hash maps    | O segredo do O(1); como a chave vira índice (hash function) de forma simples.                     |

---

## Semana 3: Arquitetura e mensageria

*Foco em sistemas distribuídos e desacoplamento (nível pleno/sênior).*

| Dia    | Tópico                   | Conteúdo sugerido para o carrossel                                                                 |
| ------ | ------------------------ | -------------------------------------------------------------------------------------------------- |
| Post 7 | Filas (queues) na prática| Por que não processar tudo na hora; papel do Redis/RabbitMQ para resiliência.                       |
| Post 8 | FIFO vs LIFO             | Casos reais: undo até filas de processamento de pagamentos.                                        |
| Post 9 | Pub/sub                  | Como desacoplar microserviços; diferença entre comando direto e evento.                            |

---

## Semana 4: IA e engenharia moderna

*Foco em tendências e padrões de design.*

| Dia     | Tópico                      | Conteúdo sugerido para o carrossel                                                                  |
| ------- | --------------------------- | --------------------------------------------------------------------------------------------------- |
| Post 10 | IA para devs: além do chat  | Integrar LLMs (OpenAI/Gemini) no backend via SDK; tokens e contexto.                                |
| Post 11 | Design patterns essenciais  | Singleton e factory; criar objetos sem “macarrão”.                                                  |
| Post 12 | Context architecture        | Organizar arquivos para ferramentas de IA (Cursor/Claude) ajudarem melhor no código.                |

---

## Dicas de implementação

### Estrutura do carrossel (7 a 10 slides)

1. **Slide 1 (capa):** título chamativo + gancho de dor (ex.: “Pare de usar if/else para tudo”).
2. **Slide 2:** o problema — por que a forma comum é ruim?
3. **Slides 3–6:** a solução técnica, com diagramas e blocos de código.
4. **Slides 7–8:** exemplo prático (sintaxe em Go, TypeScript ou C#, por exemplo).
5. **Slide 9:** resumo / takeaway — o que o dev leva para casa.
6. **Slide 10 (CTA):** “Qual dessas tecnologias você usa no dia a dia? Comenta aqui embaixo.”
