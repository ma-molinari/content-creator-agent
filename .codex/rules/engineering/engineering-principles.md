---
description: Princípios de Engenharia Sênior — SOLID, DRY/KISS/YAGNI, Clean Architecture, Early Return, RPI Cycle. Camada de padrões universais de implementação; não substitui regras ou skills de fluxo obrigatório.
alwaysApply: true
---

# Princípios de Engenharia Sênior

Camada de padrões de código universais. Aplica-se a todo trabalho de implementação neste repositório. Quando a skill `create-spec-driven` estiver ativa, o RPI Cycle abaixo reforça o fluxo — não conflita.

---

## 1. Princípios Fundamentais

### SOLID
- **SRP**: cada função, módulo ou nó faz uma coisa. Se precisar de "e" para descrever o que faz, divida.
- **OCP**: extensível via parâmetros/injeção, não por edição de lógica existente.
- **LSP**: subtipos respeitam o contrato do tipo base sem surpresas.
- **ISP**: interfaces enxutas; não force dependências de métodos que o cliente não usa.
- **DIP**: camadas superiores dependem de abstrações, não de implementações concretas.

### DRY / KISS / YAGNI
- **DRY**: extraia lógica duplicada para uma única fonte de verdade. Se copiou, extraiu.
- **KISS**: prefira a solução mais simples que funcione. Complexidade acidental é dívida.
- **YAGNI**: não crie abstrações antecipadas. Crie quando a necessidade for real e presente.

### GoF Patterns — uso condicional
Use apenas quando houver ganho real de manutenção:

| Pattern | Quando usar neste projeto |
|---------|--------------------------|
| Repository | Já adotado em Go (`repository.go`); use o padrão existente |
| Strategy | Trocar algoritmos em runtime (ex.: diferentes LLM providers) |
| Factory | Criação complexa com variantes (ex.: builders de prompt) |
| Observer | Eventos assíncronos já tratados pelo LangGraph — evite duplicar |

---

## 2. Boundaries de Clean Architecture

Mapeamento para este monorepo:

| Camada | O que é | Exemplos no projeto |
|--------|---------|---------------------|
| **Domain / Core** | Regras de negócio puras, sem imports de infra | Sentinels de erro (`ErrNotFound`, `ErrForbidden`), lógica de validação de negócio |
| **Application / Use Cases** | Orquestra domain, coordena fluxos | `service.go` (Go), nós LangGraph em `app/nodes/` (Worker) |
| **Infrastructure** | Implementações técnicas, I/O externo | `repository.go`, cliente OpenAI, boto3, Playwright, GORM |
| **Interfaces / Adapters** | Entrada/saída do sistema | `handler.go`, FastAPI endpoints em `main.py`, React components |

**Regra de ouro**: uma camada só pode importar camadas abaixo dela. `handler.go` chama `service.go`; `service.go` chama `repository.go`. Nunca o inverso.

---

## 3. Padrões de Implementação

### Typing rigoroso
- **TypeScript**: proibido `any`. Use tipos explícitos ou `unknown` + narrowing.
- **Python**: type hints obrigatórios em assinaturas; evite `Any` do `typing` — prefira `TypedDict` ou Pydantic.
- **Go**: structs tipados; evite `interface{}` sem necessidade real.

### Early Return — tratamento explícito de erros

```go
// ✅ Go — early return
func (s *service) GetChat(ctx context.Context, id string) (*Chat, error) {
    chat, err := s.repo.FindByID(ctx, id)
    if err != nil {
        return nil, err
    }
    if chat.UserID != callerID {
        return nil, ErrForbidden
    }
    return chat, nil
}
```

```python
# ✅ Python — acumula em state["errors"], não lança
def validate_node(state: AgentState) -> dict:
    if not state["profile"]:
        return {"errors": state["errors"] + ["profile missing"]}
    if not state["brief"]:
        return {"errors": state["errors"] + ["brief missing"]}
    return {}
```

```typescript
// ✅ TypeScript — early return com tipo explícito
async function fetchSlide(id: string): Promise<Slide> {
  const slide = await slideRepo.findById(id);
  if (!slide) throw new NotFoundError(`Slide ${id} not found`);
  return slide;
}
```

Evite: `try/catch` genérico que engole erros, condicionais aninhadas, retorno no `else` quando o `if` já retorna.

### Async / Concorrência
- **Worker Python**: `llm.invoke` síncrono bloqueia o event loop — use `await llm.ainvoke` ou rode em `run_in_executor` (dívida técnica #8 do projeto).
- **Go**: goroutines sempre com `defer cancel()` e `sync.WaitGroup` ou channels explícitos; sem goroutine leak.
- **Idempotência**: workers devem tolerar reprocessamento do mesmo job sem efeitos colaterais duplos.

---

## 4. RPI Cycle — antes de escrever código

Aplique sempre que a mudança tocar mais de 2 arquivos ou introduzir novo padrão:

```
1. RESEARCH  → Leia o código existente e dependências relevantes.
               Carregue docs/CONVENTIONS.md, docs/ARCHITECTURE.md conforme a tarefa.
               Não assuma — verifique.

2. PLAN      → Descreva em texto/pseudo-código a estratégia.
               Liste contratos/interfaces que mudam, arquivos tocados.
               Se >5 passos, crie tasks.md via skill create-spec-driven.

3. IMPLEMENT → Escreva o código seguindo os padrões desta regra.
               Um commit atômico por unidade lógica (Conventional Commits).

4. VERIFY    → Checklist antes de marcar como feito:
               [ ] Segue arquitetura e padrões existentes?
               [ ] Sem violação de camadas?
               [ ] Error handling explícito?
               [ ] Sem valores hardcoded configuráveis?
               [ ] Imports seguem convenções do projeto?
               [ ] Sem código de debug temporário?
               [ ] Testes existentes continuam passando?
```

---

## 5. Documentação de Código

- Documente o **"porquê"** (decisão de design, trade-off, constraint não óbvio).
- **Não** documente o **"o quê"** — o código deve ser autoexplicativo.
- Comentários que repetem o código são ruído; remova-os.

```go
// ✅ Explica decisão não óbvia
// Limite de 5 chats por usuário: ao criar o 6.º, o mais antigo é removido
// com todos os artefatos S3 para evitar acúmulo de storage órfão.
func (s *service) enforceLimit(ctx context.Context, userID string) error { ... }

// ❌ Repete o código
// Busca chat por ID
chat, err := s.repo.FindByID(ctx, id)
```
