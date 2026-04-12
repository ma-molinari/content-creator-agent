# Content Creator Agent

Um serviço web com o foco na criação de posts em redes sociais, seguindo as boas praticas e identidade visual já existente do usuário.

## Sobre

O agent será utilizado, para e apenas a criação de posts no instagram, utilizando rules e skills definidas no projeto. Os tipos de posts a serem construidos podem ser "posts single" em um unico arquivo ou o "post carrousel" que é composto por N arquivos/slides.

Os posts são criados seguindo a identidade visual já existente ou definida pelo usuário, não iremos fugir dessa identidade já utilizada, o que pode ser feito são melhorias seguindo os padrões de cores já existentes.

As estruturas de pastas, inicialmente serão preenchidas manualmente, porém em uma v2 teremos uma tela de perfil onde o proprio usuario irá poder configurar e anexar seus arquivos e conteudos de referencia seguindo o padrao estabelecido pela skill "map-instagra-profile".

Será disponibilizada uma tela de cadastro de usuarios, recuperar senha e login.
O cadastro irá disponibilizar uma chave unica de segurança, onde o usuario deve copiar e guardar em local SEGURO. Em caso de recuperação de senha, essa chave sera necessaria.

O acesso ao agent será segmentado por usuario na interface, cada usuario só pode acessar, visualizar e alterar os seus proprios conteudos. O acesso somente será permitido a usuarios atenticados.

Será diponibilizada uma tela principal, com um input de "texto/rich text", onde o usuario pode escrever seu prompt, colar um prompt ja preparado, anexar imagens de exemplo ou para uso em algum post especifico. Também teremos um icone onde o usuario pode visualizar um padrao de escrita de um bom prompt para o melhor resultado possivel. Após os arquivos criados, permitir a visualizacao e download de um arquivo unico ou todos dentro de uma pasta .zip.

Será disponibilizada uma tela onde o usuario pode selecionar 1 das ultimas 5 postagens criadas e realizar o download dos arquivos .jpg ou efetuar novos prompts para alteração do mesmo. Caso o usuario ja possua 5 posts, o mais antigo será removido e adicionado um novo post ou deletar os posts anteriores.

Todas as informações consideradas pessoais ou criticas, devem ser armazenas utilizando criptografia RSA entre front e back.

Previnir falhas de segurança, aplicar ratelimitting na API, sanitizaçao para previnir sql injection, padroes para previnir o prompt injection.

## Fluxo de trabalho

- De inicio iremos utilizar a skill "map-instagram-profile" para o setup inicial de pastas e preenchimento da estrutura obrigatória para prosseguir com o processo, caso essa etapa nao seja realizada ou os arquivos definidos pela skill sejam inexistentes, parar o processo e informar claramente ao usuario o que deve ser feito e qual o fluxo correto a ser seguido.

- O usuário poderá escrever promps em uma interface web, semelhantes as ferramentas de mercado como GPT, Claude ou Gemini. Todos os prompts devem passar pelo agent/persona "Prompt Engineering Meta" para adequação do prompt seguindo os padrões de industria para garantir um melhor resultado. Todo prompt deve utilizar ou pelo menos referenciar a skill "create-social-post", a skill é responsavel por contextualizar da melhor maneira os modelos LLms na criação de posts seguindo o design, escrita, identidade visual do usuário.

- O usuário poderá acessar uma tela de "historico", onde pode selecionar 1 de seus 5 ultimos chats/posts criados, onde pode realizar alguma alteração se necessario e efetuar download dos arquivos ou ate mesmo deletar os posts desejados.

- Existirá um cron-job que rodará uma vez ao dia, sua funcao é analisar o chat existente e criar um resumo (utilizando o GPT-5.4 mini) para que, caso seja necessário alteração futura, o conteudo reutilizado como contexto seja compacto e gaste menos tokens.
  O cron-job só irá criar/atualizar o resumo, caso existam alterações recentes no chat, será realizado uma comparação entre a data do conteudo mais recente com a data do resumo.

## Technologia

### Front-end

- React
- Tanstack Query
- Zustand
- Zod
- shadcn
- Tailwind

##

### Back-end

- Golang
- Amazon S3
- Gorm
- Echo

### Worker (Processamento)

- Python + LangGraph
- Playwright (playwright-python)
- boto3 (Amazon S3)
- FastAPI (ou Flask) para endpoint de recebimento de jobs

### LLM (geração de conteúdo)

- OpenAI GPT-5.4 Mini (pipeline no worker Python)

##

### Banco

- Postgres
- Redis (opcional)

#### Tabelas

- users
- chats
- chat_content
- chat_content_image
- chat_content_resume
- jobs (estado assíncrono de processamento; API Go + worker Python)

OBS: os campos das tabelas serão definidos em conjuntos com o Agent/LLM na criação do plano e desenvolvimento.
