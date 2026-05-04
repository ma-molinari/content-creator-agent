# Iterative Slide Refinement — Context

**Coletado em**: 2026-05-03
**Spec**: `.specs/features/iterative-slide-refinement/spec.md`
**Status**: Pronto para design

---

## Feature Boundary

Dentro de um mesmo chat, prompts subsequentes à primeira geração de slides devem editar os slides existentes em vez de regenerar do zero. O sistema detecta automaticamente se a intenção é refinamento ou nova criação. Cada geração cria uma versão com seus JPEGs + HTML fonte; versões anteriores ficam acessíveis para download no thread.

---

## Implementation Decisions

### Detecção de intenção (editar vs. criar do zero)

- O sistema usa inferência automática pelo LLM — **sem toggle manual do usuário**
- O worker recebe os HTMLs da versão mais recente como contexto adicional
- O system prompt instrui o LLM a decidir: se o prompt refina/modifica → edita os HTMLs recebidos; se é um tema/criação nova → gera do zero ignorando o contexto
- Sem "modo explícito" no frontend — a detecção é implícita e transparente
- Se houver falsos positivos frequentes em produção, um toggle pode ser adicionado como P2 em V2

### Escopo das edições

- Qualquer alteração que o usuário pedir via prompt: texto, cores, fontes, layout, estrutura, número de slides
- O LLM tem liberdade total para modificar os HTMLs recebidos conforme instruído
- O número de slides pode mudar em um refinamento (não é fixo)

### Armazenamento e histórico de versões

- HTML fonte de cada geração armazenado no **S3** (não no banco de dados)
  - Motivo: HTMLs podem ter vários KB por slide; S3 é o lugar correto para blobs
  - Chave: `slides/{userID}/{chatID}/{jobID}/slide_{n}.html`
- O banco armazena apenas as **chaves S3** dos HTMLs (nova coluna em `chat_content_image` ou nova tabela)
- Cada round de geração = uma versão; versões anteriores NÃO são deletadas
- O usuário não "restaura" versões — ele baixa a versão anterior e usa como referência

### Feedback visual no frontend

- **Substituição silenciosa**: os novos slides substituem os da mensagem correspondente sem animação ou destaque
- Cada mensagem de assistente no thread continua exibindo seus slides individualmente (já funciona assim)
- Identificação de versão anterior: label visual simples (ex.: "Versão anterior") nas mensagens que não são a mais recente no thread
- Download por versão: cada mensagem de assistente com slides tem seu próprio botão de download (ZIP dos JPEGs daquela versão apenas)

### Agent's Discretion

- Design do sistema prompt de detecção de intenção (wording exato, exemplos, threshold) — o agente decide a melhor formulação durante o design
- Estratégia de fallback quando HTML fonte não está acessível (S3 timeout/erro) — já definido como "gerar do zero com log", implementação exata fica a critério do agente
- Schema exato da nova coluna/tabela no banco para as chaves S3 dos HTMLs

---

## Specific References

- O usuário citou o caso concreto: "quero alterar um pequeno elemento ou texto nos slides já existentes"
- Expectativa: mesma qualidade visual da geração inicial, só com o elemento pedido alterado
- O usuário validou que "download manual de versão anterior" substitui rollback automático no V1

---

## Deferred Ideas

- Toggle explícito "editar / criar novo" no frontend — adiado para V2 se detecção automática gerar falsos positivos
- Diff visual "antes vs. depois" por slide — V2
- Edição granular slide a slide com seleção no frontend — V2
- Restauração automática de versão anterior (rollback) — V2
