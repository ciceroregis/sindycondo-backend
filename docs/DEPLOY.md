# Manual de Deploy — SindyCondo

## Índice
1. [Infraestrutura](#infraestrutura)
2. [Setup inicial do VPS](#setup-inicial-do-vps)
3. [Deploy de Produção — Backend](#deploy-de-produção--backend)
4. [Deploy de TU — Backend](#deploy-de-tu--backend)
5. [Gerenciamento de Containers](#gerenciamento-de-containers)
6. [Banco de Dados](#banco-de-dados)
7. [Resolução de Problemas](#resolução-de-problemas)

---

## Infraestrutura

| Ambiente | Branch | Diretório VPS | Domínio API | Imagem Docker |
|----------|--------|---------------|-------------|---------------|
| Produção | `main` | `/opt/sindycondo/` | `api.sindycondo.com.br` | `:latest` |
| TU | `develop` | `/opt/sindycondo-tu/` | `tu.api.sindycondo.com.br` | `:develop` |

**Serviços compartilhados (Produção):**
- Traefik → `traefik.sindycondo.com.br`
- Portainer → `portainer.sindycondo.com.br`

**Serviços por ambiente:**
- API Django + Celery
- PostgreSQL (volumes isolados)
- Redis
- pgAdmin → `db.sindycondo.com.br` (prod) / `tu.db.sindycondo.com.br` (TU)

---

## Setup inicial do VPS

### 1. Instalar Docker
```bash
curl -fsSL https://get.docker.com | sh
usermod -aG docker $USER
```

### 2. Criar diretórios
```bash
# Produção
sudo mkdir -p /opt/sindycondo/traefik
sudo chown cicero:cicero /opt/sindycondo

# TU
sudo mkdir -p /opt/sindycondo-tu
sudo chown cicero:cicero /opt/sindycondo-tu
```

### 3. Criar .env de Produção
```bash
nano /opt/sindycondo/.env
```
```env
DEBUG=False
SECRET_KEY=<gerar com: python3 -c "import secrets; print(secrets.token_urlsafe(50))">

GITHUB_IMAGE=ciceroregis/sindycondo-backend

POSTGRES_DB=sindycondo
POSTGRES_USER=sindycondo_user
POSTGRES_PASSWORD=<senha>
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/0

ALLOWED_HOSTS=api.sindycondo.com.br
CORS_ALLOWED_ORIGINS=https://sindycondo.com.br,https://www.sindycondo.com.br

ADMIN_URL_PATH=admin/
ENVIRONMENT=production

TRAEFIK_AUTH=admin:<hash gerado com htpasswd -nB>
PGADMIN_EMAIL=admin@sindycondo.com.br
PGADMIN_PASSWORD=<senha>
```

### 4. Criar .env de TU
```bash
nano /opt/sindycondo-tu/.env
```
```env
DEBUG=False
SECRET_KEY=<mesma ou diferente da produção>

GITHUB_IMAGE=ciceroregis/sindycondo-backend

POSTGRES_DB=sindycondo_tu
POSTGRES_USER=sindycondo_tu
POSTGRES_PASSWORD=<senha>
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

REDIS_URL=redis://redis:6379/0

ALLOWED_HOSTS=tu.api.sindycondo.com.br
CORS_ALLOWED_ORIGINS=https://tu.sindycondo.com.br

ADMIN_URL_PATH=admin/
ENVIRONMENT=tu

PGADMIN_EMAIL=admin@sindycondo.com.br
PGADMIN_PASSWORD=<senha>
```

### 5. Gerar hash para Traefik dashboard
```bash
docker run --rm httpd:alpine htpasswd -nbB admin "SuaSenha"
# Output: admin:$2y$...
# No .env, duplicar todos os $ → admin:$$2y$$...
```

### 6. Configurar secrets no GitHub
Em `github.com/ciceroregis/sindycondo-backend` → Settings → Secrets → Actions:

| Secret | Valor |
|--------|-------|
| `VPS_HOST` | IP ou domínio do VPS |
| `VPS_USER` | `cicero` |
| `VPS_SSH_KEY` | Conteúdo da chave privada SSH |
| `VPS_PORT` | `22` (ou porta configurada) |

---

## Deploy de Produção — Backend

### Automático (CI/CD)
```bash
git checkout main
git push origin main
# GitHub Actions dispara automaticamente
# Acompanhar: github.com/ciceroregis/sindycondo-backend/actions
```

### Manual no VPS
```bash
cd /opt/sindycondo

# Baixar imagem mais recente
docker compose pull api celery

# Subir containers atualizados
docker compose up -d --no-deps api celery

# Verificar status
docker compose ps
docker compose logs api --tail=30
```

### Primeiro deploy (sobe tudo)
```bash
cd /opt/sindycondo
docker compose up -d
```

### Criar superusuário admin
```bash
docker compose exec api python manage.py createsuperuser
```

---

## Deploy de TU — Backend

### Automático (CI/CD)
```bash
git checkout develop
git push origin develop
# GitHub Actions dispara automaticamente
# Acompanhar: github.com/ciceroregis/sindycondo-backend/actions
```

### Acionamento manual do pipeline
```
github.com/ciceroregis/sindycondo-backend/actions/workflows/deploy-tu.yml
→ Run workflow → branch: develop → Run
```

### Manual no VPS
```bash
cd /opt/sindycondo-tu

# Subir todos os serviços
GITHUB_IMAGE=ciceroregis/sindycondo-backend docker compose -f docker-compose.tu.yml up -d

# Atualizar apenas API e Celery
GITHUB_IMAGE=ciceroregis/sindycondo-backend docker compose -f docker-compose.tu.yml up -d --force-recreate api celery

# Verificar status
docker compose -f docker-compose.tu.yml ps
docker compose -f docker-compose.tu.yml logs api --tail=30
```

### Criar superusuário admin TU
```bash
docker compose -f /opt/sindycondo-tu/docker-compose.tu.yml exec api python manage.py createsuperuser
```

### Propagar fixes de develop para produção
```bash
git checkout main
git merge develop
git push origin main
```

---

## Gerenciamento de Containers

### Ver status
```bash
# Produção
docker compose -f /opt/sindycondo/docker-compose.yml ps

# TU
docker compose -f /opt/sindycondo-tu/docker-compose.tu.yml ps

# Todos os containers do VPS
docker ps
```

### Reiniciar containers
```bash
# Produção
cd /opt/sindycondo && docker compose restart api celery

# TU
cd /opt/sindycondo-tu && docker compose -f docker-compose.tu.yml restart api celery
```

### Parar e subir tudo
```bash
# Produção
cd /opt/sindycondo && docker compose down && docker compose up -d

# TU
cd /opt/sindycondo-tu && docker compose -f docker-compose.tu.yml down && \
  GITHUB_IMAGE=ciceroregis/sindycondo-backend docker compose -f docker-compose.tu.yml up -d
```

### Ver logs
```bash
# API produção (tempo real)
docker logs sindycondo-api-1 -f

# API TU (últimas 50 linhas)
docker logs sindycondo-tu-api-1 --tail=50

# Traefik
docker logs sindycondo-traefik-1 --tail=30
```

---

## Banco de Dados

### Conexão pgAdmin — Produção (`db.sindycondo.com.br`)
| Campo | Valor |
|-------|-------|
| Host | `postgres` |
| Port | `5432` |
| Database | `sindycondo` |
| Username | `sindycondo_user` |
| Password | conforme `.env` |

### Conexão pgAdmin — TU (`tu.db.sindycondo.com.br`)
| Campo | Valor |
|-------|-------|
| Host | `postgres` |
| Port | `5432` |
| Database | `sindycondo_tu` |
| Username | `sindycondo_tu` |
| Password | conforme `.env` |

### Resetar banco do TU (apaga todos os dados)
```bash
cd /opt/sindycondo-tu
docker compose -f docker-compose.tu.yml down
docker rm -f sindycondo-tu-postgres-1 2>/dev/null || true
docker volume rm sindycondo-tu_postgres_data
GITHUB_IMAGE=ciceroregis/sindycondo-backend docker compose -f docker-compose.tu.yml up -d
```

### Rodar migrations manualmente
```bash
# Produção
docker compose -f /opt/sindycondo/docker-compose.yml exec api python manage.py migrate

# TU
docker compose -f /opt/sindycondo-tu/docker-compose.tu.yml exec api python manage.py migrate
```

---

## Resolução de Problemas

### Container reiniciando em loop
```bash
docker logs <nome-container> --tail=50
```

### CORS bloqueando frontend
Adicionar domínio ao `.env`:
```
CORS_ALLOWED_ORIGINS=https://dominio.com.br,https://outro.com.br
```
Depois: `docker compose restart api`

### Certificado SSL inválido (NET::ERR_CERT_AUTHORITY_INVALID)
Aguardar Traefik emitir o certificado via Let's Encrypt (~2 min). Verificar:
```bash
docker logs sindycondo-traefik-1 --tail=30 | grep -i cert
```

### Volume postgres com credenciais antigas
```bash
docker compose down
docker rm -f <container-id-do-postgres>
docker volume rm <nome-do-volume>_postgres_data
docker compose up -d
```

### Middleware https-redirect não encontrado
Garantir que o container `traefik` está rodando — ele é quem define esse middleware global.

### Imagem Docker antiga sendo usada
```bash
docker rmi ghcr.io/ciceroregis/sindycondo-backend:latest --force
docker pull ghcr.io/ciceroregis/sindycondo-backend:latest
docker compose up -d --force-recreate api celery
```
