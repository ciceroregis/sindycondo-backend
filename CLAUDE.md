# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

```bash
# Ativar virtualenv
source venv/bin/activate

# Rodar servidor local
python manage.py runserver

# Aplicar migrations
python manage.py migrate

# Criar migration após alterar models
python manage.py makemigrations

# Criar superusuário
python manage.py createsuperuser

# Rodar shell Django
python manage.py shell
```

Dependências de infra local necessárias: PostgreSQL (`sindycondo` / `postgres`) e Redis (`localhost:6379`). As variáveis ficam em `.env` na raiz (ver `.env.production.example`).

## Arquitetura

### Stack
- Django 5.0 + DRF + PostgreSQL
- Autenticação: JWT via `djangorestframework-simplejwt` com blacklist ativo
- Tempo real: Django Channels + Redis
- Tarefas assíncronas: Celery (broker Redis)
- ASGI em produção: Gunicorn + UvicornWorker

### Estrutura do código

Todo o domínio está em `api/gestao/`:

| Arquivo | Responsabilidade |
|---------|-----------------|
| `models.py` | Condominio, Usuario (herda User), Garagem, Visitante, RegistroAcesso, AuditLog |
| `serializers.py` | Validações de negócio (síndico único, titular/dependente, limite de vagas) |
| `views.py` | ViewSets + dashboard_stats + health_check |
| `permissions.py` | IsAdmin, IsAdminOrSindico, IsPorteiroOrAbove, IsMesmoCondominio |
| `authentication.py` | Login via CPF ou e-mail (substitui username padrão) |
| `admin.py` | Admin Django completo para todos os modelos |
| `urls.py` | Router: condominios/, garagens/, usuarios/, dashboard/stats/ |

`sindycondo/urls.py` monta os prefixos `api/auth/`, `api/`, `api/health/` e a documentação Swagger em `api/docs/`.

### Modelo Usuario
Usa **multi-table inheritance** de `django.contrib.auth.models.User`. Acesso via `request.user.usuario` (pode falhar se o User não tiver perfil Usuario — use `_get_usuario(user)` de `views.py`).

Tipos: `admin`, `sindico`, `porteiro`, `morador`. Papéis (moradores): `titular`, `dependente`.

`is_active=False` = pendente de aprovação. Moradores criados pelo registro público iniciam com `is_active=False`.

### Regras de visibilidade (get_queryset padrão)
- superuser / admin → vê tudo
- sindico / porteiro → apenas seu condomínio
- morador → apenas a si mesmo

### Fluxo de senha automática
Ao criar usuário via `UsuarioSerializer.create()`, a senha inicial é gerada como `{cpf_digits}{apartamento}`. O username é gerado por `_gerar_username()` no formato `nome.sobrenome.apto`.

## Deploy

CI/CD via GitHub Actions (`.github/workflows/deploy.yml`):
1. Push em `main` → build da imagem Docker → push para GHCR (`ghcr.io/ciceroregis/sindycondo-backend`)
2. SSH no VPS → baixa `docker-compose.yml` e `traefik/traefik.yml` via curl do GitHub Raw → pull da imagem → restart dos containers

**Secrets necessários no GitHub:** `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, `VPS_PORT`

No VPS (`/opt/sindycondo/`): apenas o `.env` precisa existir manualmente — o resto é gerenciado pelo workflow.

Infra no VPS: Traefik (proxy reverso + TLS automático via Let's Encrypt) + API + Celery + PostgreSQL + Redis, todos em Docker Compose.

## Fases do projeto

- **Fase 1** ✅ — Auth, Condomínios, Usuários
- **Fase 2** 🔜 — CRUD Visitante, QR Code (geração + validação), Registro de Acesso
- **Fase 3** 🔜 — Reconhecimento facial, notificações (Twilio/Firebase), WebSockets
- **Fase 4** 🔜 — Testes, AuditLog LGPD completo
