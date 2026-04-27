# Guia de Deploy — Content Creator Agent (EC2 + RDS + S3)

Este documento descreve como colocar a stack em produção em uma instância EC2 com RDS PostgreSQL e S3.

---

## Arquitetura de rede recomendada

```
Internet
  │
  │ 443 / 80
  ▼
[ Nginx (EC2 público) ] — TLS termination (Let's Encrypt ou ACM)
  │
  │ 127.0.0.1:8080
  ▼
[ API Go (Docker) ]
  │
  │ 127.0.0.1:8000  (rede Docker interna)
  ▼
[ Worker Python (Docker) ]
  │
  ├── RDS PostgreSQL (VPC privada, porta 5432)
  └── S3 (via endpoint de VPC ou HTTPS público)
```

### Security Groups recomendados

| SG | Origem | Porta | Destino |
|----|--------|-------|---------|
| `sg-ec2` | 0.0.0.0/0 | 443, 80 | Nginx |
| `sg-ec2` | sg-ec2 | 8080 | API Go (apenas localhost/Docker) |
| `sg-ec2` | sg-ec2 | 8000 | Worker Python (apenas Docker interno) |
| `sg-rds` | sg-ec2 | 5432 | RDS PostgreSQL |

> A API e o Worker **não devem** ser expostos diretamente à Internet. Apenas o Nginx recebe tráfego externo.

---

## Pré-requisitos

- Instância EC2 (Amazon Linux 2023 ou Ubuntu 22.04+), mínimo `t3.small`
- RDS PostgreSQL 16, em subnet privada, com `sslmode=require`
- Bucket S3 criado; prefira IAM Instance Profile (sem chaves hardcoded)
- Docker e Docker Compose v2 instalados na instância

---

## Checklist de deploy

### 1. Clonar o repositório

```bash
git clone <repo-url> /opt/app
cd /opt/app
```

### 2. Gerar secrets

```bash
openssl rand -hex 32   # JWT_SECRET
openssl rand -hex 32   # JWT_REFRESH_SECRET
openssl rand -hex 32   # WORKER_API_KEY
```

### 3. Criar o arquivo de variáveis de ambiente

Crie `/opt/app/.env.production` com as variáveis abaixo (nunca commite este arquivo):

```env
# Banco de dados
DATABASE_URL=postgres://user:password@rds-host:5432/dbname?sslmode=require

# JWT
JWT_SECRET=<gerado acima>
JWT_REFRESH_SECRET=<gerado acima>

# Worker
WORKER_API_KEY=<gerado acima>
WORKER_URL=http://worker:8000

# AWS — prefira Instance Profile; preencha apenas se não usar IAM role
AWS_REGION=us-east-1
AWS_S3_BUCKET=meu-bucket
# AWS_ACCESS_KEY_ID=     # omitir se usar Instance Profile
# AWS_SECRET_ACCESS_KEY= # omitir se usar Instance Profile

# Cookie / HTTPS
COOKIE_SECURE=true
CORS_ALLOWED_ORIGINS=https://meudominio.com

# OpenAI (obrigatório no worker; opcional na API para cron de sumarização)
OPENAI_API_KEY=sk-...

# Cron (opcional, padrão já definido)
# SUMMARIZE_CRON=0 2 * * *
# STUCK_JOB_CRON=*/15 * * * *
```

### 4. Configurar IAM Instance Profile (recomendado)

Em vez de chaves de acesso, crie uma IAM role com a policy abaixo e associe à instância:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::meu-bucket",
        "arn:aws:s3:::meu-bucket/*"
      ]
    }
  ]
}
```

### 5. Subir a stack

```bash
cd /opt/app
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file .env.production up -d --build
```

### 6. Configurar Nginx como proxy reverso com TLS

Instale o Nginx e o Certbot:

```bash
sudo apt install -y nginx certbot python3-certbot-nginx   # Ubuntu
# ou
sudo dnf install -y nginx certbot python3-certbot-nginx   # Amazon Linux 2023
```

Arquivo `/etc/nginx/sites-available/content-creator`:

```nginx
server {
    listen 80;
    server_name meudominio.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name meudominio.com;

    ssl_certificate     /etc/letsencrypt/live/meudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/meudominio.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # Limite de body (alinhado ao BodyLimit da API)
    client_max_body_size 2m;

    location / {
        proxy_pass         http://127.0.0.1:8080;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/content-creator /etc/nginx/sites-enabled/
sudo certbot --nginx -d meudominio.com
sudo systemctl reload nginx
```

---

## Variáveis de ambiente obrigatórias em produção

| Variável | Serviço | Notas |
|----------|---------|-------|
| `DATABASE_URL` | API | Postgres com `sslmode=require` |
| `JWT_SECRET` | API | ≥ 32 bytes aleatórios |
| `JWT_REFRESH_SECRET` | API | ≥ 32 bytes aleatórios, diferente do anterior |
| `WORKER_API_KEY` | API + Worker | Mesmo valor nos dois serviços |
| `WORKER_URL` | API | `http://worker:8000` na rede Docker |
| `AWS_REGION` | API + Worker | Ex.: `us-east-1` |
| `AWS_S3_BUCKET` | API + Worker | Nome do bucket |
| `COOKIE_SECURE` | API | `true` obrigatório em HTTPS |
| `OPENAI_API_KEY` | Worker (obrig.) / API (opcional) | Habilita cron de sumarização na API |

---

## Comandos de verificação pós-deploy

```bash
# Health da API
curl -f https://meudominio.com/health

# Health do Worker (via rede interna Docker)
docker exec content-creator-api-1 wget -qO- http://worker:8000/health

# Logs da API
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f api

# Logs do Worker
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f worker

# Verificar que containers rodam como não-root
docker inspect --format '{{.Config.User}}' <container-id>

# Status das migrações (deve mostrar versão 10)
docker exec content-creator-api-1 /app/server --migrations-status 2>/dev/null || true
```

---

## Renovação automática do certificado TLS

```bash
# Adicionar ao cron do root
echo "0 3 * * * certbot renew --quiet && systemctl reload nginx" | sudo crontab -
```

---

## Notas de segurança

- **Nunca** exponha as portas 8080 (API) ou 8000 (Worker) diretamente ao Security Group público.
- **Nunca** commite `.env.production`, segredos ou chaves AWS no repositório.
- O `WORKER_API_KEY` autentica a comunicação API → Worker; use um valor longo e aleatório.
- O `COOKIE_SECURE=true` é obrigatório para que o refresh token HttpOnly funcione corretamente via HTTPS.
- Refresh tokens agora são registrados e revogados server-side (tabela `refresh_tokens`). Em caso de comprometimento, remova o registro diretamente no banco: `DELETE FROM refresh_tokens WHERE user_id = '<uuid>';`
