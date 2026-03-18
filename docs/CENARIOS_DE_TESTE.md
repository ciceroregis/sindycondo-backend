# Cenários de Teste — SindyCondo API

**Versão:** 1.0
**Ambiente TU:** `https://tu.api.sindycondo.com.br`
**Swagger:** `https://tu.api.sindycondo.com.br/api/docs/`
**Data:** 2026-03-12

---

## Índice
1. [Autenticação](#1-autenticação)
2. [Condomínios](#2-condomínios)
3. [Usuários](#3-usuários)
4. [Garagens](#4-garagens)
5. [Dashboard](#5-dashboard)
6. [Controle de Acesso por Papel](#6-controle-de-acesso-por-papel)

---

## 1. Autenticação

### CT-AUTH-01 — Login com CPF válido
**Pré-condição:** Usuário cadastrado com CPF `000.000.000-00`
**Endpoint:** `POST /api/auth/login/`
**Payload:**
```json
{ "login": "000.000.000-00", "password": "00000000000101" }
```
**Resultado esperado:** `200 OK` com `access` e `refresh` tokens

---

### CT-AUTH-02 — Login com CPF sem formatação
**Endpoint:** `POST /api/auth/login/`
**Payload:**
```json
{ "login": "00000000000", "password": "00000000000101" }
```
**Resultado esperado:** `200 OK` — sistema aceita CPF com ou sem máscara

---

### CT-AUTH-03 — Login com e-mail
**Endpoint:** `POST /api/auth/login/`
**Payload:**
```json
{ "login": "usuario@email.com", "password": "senha123" }
```
**Resultado esperado:** `200 OK` com tokens

---

### CT-AUTH-04 — Login com credenciais inválidas
**Endpoint:** `POST /api/auth/login/`
**Payload:**
```json
{ "login": "naoexiste@email.com", "password": "errado" }
```
**Resultado esperado:** `401 Unauthorized` — `"CPF/e-mail ou senha inválidos."`

---

### CT-AUTH-05 — Login com usuário inativo
**Pré-condição:** Morador com `is_active=False` (pendente de aprovação)
**Resultado esperado:** `401 Unauthorized` — `"Usuário inativo. Entre em contato com o síndico."`

---

### CT-AUTH-06 — Renovar token
**Endpoint:** `POST /api/auth/refresh/`
**Payload:**
```json
{ "refresh": "<token_de_refresh>" }
```
**Resultado esperado:** `200 OK` com novo `access` token

---

### CT-AUTH-07 — Logout (blacklist do token)
**Endpoint:** `POST /api/auth/logout/`
**Header:** `Authorization: Bearer <access_token>`
**Payload:**
```json
{ "refresh": "<token_de_refresh>" }
```
**Resultado esperado:** `200 OK`. Tentar usar o refresh token novamente deve retornar `401`.

---

### CT-AUTH-08 — Acesso sem token
**Endpoint:** `GET /api/usuarios/`
**Resultado esperado:** `401 Unauthorized`

---

## 2. Condomínios

### CT-COND-01 — Criar condomínio (admin)
**Endpoint:** `POST /api/condominios/`
**Papel:** `admin`
**Payload:**
```json
{
  "nome": "Residencial Teste",
  "endereco": "Rua das Flores, 100",
  "cnpj": "12.345.678/0001-90",
  "cidade": "São Paulo",
  "estado": "SP",
  "blocos": 2,
  "total_apartamentos": 20,
  "total_vagas": 10
}
```
**Resultado esperado:** `201 Created` + 10 garagens criadas automaticamente (numeradas de 1 a 10)

---

### CT-COND-02 — Criar condomínio sem permissão
**Papel:** `sindico` ou `morador`
**Resultado esperado:** `403 Forbidden`

---

### CT-COND-03 — CNPJ duplicado
**Pré-condição:** Condomínio com CNPJ `12.345.678/0001-90` já existe
**Resultado esperado:** `400 Bad Request` — `"Já existe um condomínio cadastrado com este CNPJ."`

---

### CT-COND-04 — Listar condomínios por papel
| Papel | Resultado esperado |
|-------|--------------------|
| `admin` | Todos os condomínios |
| `sindico` | Apenas seu condomínio |
| `porteiro` | Apenas seu condomínio |
| `morador` | Apenas seu condomínio |

---

### CT-COND-05 — Aumentar total de vagas
**Endpoint:** `PATCH /api/condominios/{id}/`
**Papel:** `admin` ou `sindico`
**Payload:** `{ "total_vagas": 15 }`
**Resultado esperado:** `200 OK` + 5 novas garagens criadas automaticamente

---

### CT-COND-06 — Reduzir total de vagas abaixo do cadastrado
**Pré-condição:** 10 garagens cadastradas
**Payload:** `{ "total_vagas": 5 }`
**Resultado esperado:** `400 Bad Request` — `"Não é possível reduzir para 5. Já existem 10 garagem(ns) cadastrada(s)."`

---

### CT-COND-07 — Reduzir total de apartamentos abaixo de titulares cadastrados
**Pré-condição:** 8 titulares cadastrados
**Payload:** `{ "total_apartamentos": 5 }`
**Resultado esperado:** `400 Bad Request` — mensagem informando o número de titulares existentes

---

## 3. Usuários

### CT-USU-01 — Criar síndico
**Endpoint:** `POST /api/usuarios/`
**Papel:** `admin` ou `sindico`
**Payload:**
```json
{
  "nome": "João Silva",
  "email": "joao@email.com",
  "cpf": "123.456.789-00",
  "tipo": "sindico",
  "condominio": 1
}
```
**Resultado esperado:** `201 Created`. Username gerado automaticamente: `joao.silva`. Senha gerada: `12345678900` (CPF sem formatação).

---

### CT-USU-02 — Criar segundo síndico no mesmo condomínio
**Pré-condição:** Condomínio já possui um síndico
**Resultado esperado:** `400 Bad Request` — `"Este condomínio já possui um síndico."`

---

### CT-USU-03 — Criar morador titular
**Payload:**
```json
{
  "nome": "Maria Santos",
  "email": "maria@email.com",
  "cpf": "987.654.321-00",
  "tipo": "morador",
  "papel": "titular",
  "apartamento": 101,
  "bloco": "A",
  "condominio": 1
}
```
**Resultado esperado:** `201 Created`. Senha gerada: `98765432100101` (CPF + apartamento).

---

### CT-USU-04 — Criar dependente sem titular no apartamento
**Payload:**
```json
{
  "nome": "Pedro Santos",
  "tipo": "morador",
  "papel": "dependente",
  "apartamento": 202,
  "bloco": "B",
  "condominio": 1
}
```
**Resultado esperado:** `400 Bad Request` — `"Não existe titular cadastrado no apartamento 202 do bloco B."`

---

### CT-USU-05 — Criar titular duplicado no mesmo apartamento/bloco
**Pré-condição:** Titular já cadastrado no apt 101, bloco A
**Resultado esperado:** `400 Bad Request` — `"Já existe um titular cadastrado no apartamento 101 do bloco A."`

---

### CT-USU-06 — Criar morador sem número de apartamento
**Payload:** `{ "tipo": "morador", "papel": "titular" }` sem `apartamento`
**Resultado esperado:** `400 Bad Request` — `"Número do apartamento é obrigatório para moradores."`

---

### CT-USU-07 — Criar morador sem bloco
**Payload:** com `apartamento` mas sem `bloco`
**Resultado esperado:** `400 Bad Request` — `"Identificação do bloco é obrigatória para moradores."`

---

### CT-USU-08 — Exceder limite de apartamentos
**Pré-condição:** Condomínio com `total_apartamentos=5`, 5 titulares já cadastrados
**Resultado esperado:** `400 Bad Request` — `"Limite atingido. O condomínio permite no máximo 5 titular(es)."`

---

### CT-USU-09 — Aprovar cadastro de morador
**Endpoint:** `PATCH /api/usuarios/{id}/aprovar/`
**Papel:** `admin` ou `sindico`
**Pré-condição:** Morador com `is_active=False`
**Resultado esperado:** `200 OK` — `"Morador aprovado com sucesso."` + `is_active=True`

---

### CT-USU-10 — Listar pendentes de aprovação
**Endpoint:** `GET /api/usuarios/pendentes/`
**Papel:** `admin` ou `sindico`
**Resultado esperado:** `200 OK` com lista de moradores `is_active=False`

---

### CT-USU-11 — Visualizar próprio perfil
**Endpoint:** `GET /api/usuarios/me/`
**Resultado esperado:** `200 OK` com dados do usuário autenticado

---

### CT-USU-12 — Morador atualiza próprio perfil
**Endpoint:** `PATCH /api/usuarios/me_update/`
**Papel:** `morador`
**Payload:** `{ "telefone": "(11) 99999-9999" }`
**Resultado esperado:** `200 OK` com dados atualizados

---

### CT-USU-13 — Morador tenta alterar tipo/apartamento
**Endpoint:** `PATCH /api/usuarios/me_update/`
**Payload:** `{ "tipo": "admin", "apartamento": 999 }`
**Resultado esperado:** Campos ignorados — apenas `email`, `nome`, `telefone`, `foto`, preferências de notificação e senha são permitidos

---

### CT-USU-14 — Alterar senha do próprio perfil
**Endpoint:** `PATCH /api/usuarios/me_update/`
**Payload:**
```json
{
  "senha_atual": "senhaatual123",
  "nova_senha": "novasenha456"
}
```
**Resultado esperado:** `200 OK`. Login com nova senha deve funcionar.

---

### CT-USU-15 — Alterar senha com senha atual incorreta
**Payload:** `{ "senha_atual": "errada", "nova_senha": "nova123" }`
**Resultado esperado:** `400 Bad Request` — `"Senha atual incorreta."`

---

### CT-USU-16 — E-mail duplicado
**Pré-condição:** `email@teste.com` já cadastrado
**Resultado esperado:** `400 Bad Request` — `"Este e-mail já está cadastrado."`

---

## 4. Garagens

### CT-GAR-01 — Listar garagens do condomínio
**Endpoint:** `GET /api/garagens/`
**Resultado esperado:** `200 OK` com vagas ordenadas por número (ordem natural: 1, 2, ..., 10)

---

### CT-GAR-02 — Filtrar vagas disponíveis
**Endpoint:** `GET /api/garagens/?disponivel=true`
**Resultado esperado:** `200 OK` com apenas vagas sem morador atribuído

---

### CT-GAR-03 — Atribuir vaga a morador titular
**Endpoint:** `PATCH /api/garagens/{id}/`
**Papel:** `admin` ou `sindico`
**Payload:** `{ "morador": <id_do_titular> }`
**Resultado esperado:** `200 OK` com `disponivel: false`

---

### CT-GAR-04 — Atribuir vaga a dependente
**Pré-condição:** Morador com `papel=dependente`
**Resultado esperado:** `400 Bad Request` — `"Somente titulares podem ter vaga atribuída."`

---

### CT-GAR-05 — Atribuir terceira vaga ao mesmo morador
**Pré-condição:** Morador já possui 2 vagas atribuídas
**Resultado esperado:** `400 Bad Request` — `"Este morador já possui 2 vagas atribuídas (limite máximo)."`

---

### CT-GAR-06 — Atribuir morador de outro condomínio
**Resultado esperado:** `400 Bad Request` — `"Este morador não pertence ao condomínio desta garagem."`

---

### CT-GAR-07 — Criar vaga autônoma sem matrícula
**Payload:** `{ "tipo": "autonoma", "numero": "A01" }` sem `matricula`
**Resultado esperado:** `400 Bad Request` — `"Matrícula é obrigatória para vagas autônomas."`

---

### CT-GAR-08 — Matrícula duplicada no mesmo condomínio
**Pré-condição:** Vaga com matrícula `MAT-001` já existe
**Resultado esperado:** `400 Bad Request` — `"Já existe uma vaga com a matrícula MAT-001 neste condomínio."`

---

### CT-GAR-09 — Excluir vaga ocupada
**Endpoint:** `DELETE /api/garagens/{id}/`
**Pré-condição:** Vaga com morador atribuído
**Resultado esperado:** `400 Bad Request` — `"A garagem {N} está ocupada por {nome}. Retire o morador da vaga antes de excluí-la."`

---

### CT-GAR-10 — Exceder limite de vagas do condomínio
**Pré-condição:** Condomínio com `total_vagas=10`, 10 vagas já cadastradas
**Resultado esperado:** `400 Bad Request` — `"Limite atingido. O condomínio permite no máximo 10 vaga(s)."`

---

### CT-GAR-11 — Número de vaga duplicado no condomínio
**Payload:** `{ "numero": "5" }` onde `5` já existe
**Resultado esperado:** `400 Bad Request` — `"A garagem 5 já está cadastrada neste condomínio."`

---

## 5. Dashboard

### CT-DASH-01 — Obter estatísticas do condomínio
**Endpoint:** `GET /api/dashboard/stats/`
**Resultado esperado:** `200 OK` com:
```json
{
  "total_moradores": 15,
  "moradores_mes": 3,
  "total_vagas": 10,
  "vagas_disponiveis": 4,
  "total_visitantes_hoje": 2,
  "total_acessos_hoje": 5,
  "acessos_negados_hoje": 1,
  "visitantes_pendentes": 0
}
```

---

### CT-DASH-02 — Dashboard sem condomínio associado
**Pré-condição:** Usuário sem `condominio` definido
**Resultado esperado:** `404 Not Found` — `"Perfil não encontrado."`

---

## 6. Controle de Acesso por Papel

### CT-ACL-01 — Matriz de permissões

| Ação | admin | sindico | porteiro | morador |
|------|-------|---------|----------|---------|
| Criar condomínio | ✅ | ❌ | ❌ | ❌ |
| Editar condomínio | ✅ | ✅ | ❌ | ❌ |
| Criar usuário | ✅ | ✅ | ❌ | ❌ |
| Editar usuário | ✅ | ✅ | ❌ | ❌ |
| Excluir usuário | ✅ | ❌ | ❌ | ❌ |
| Aprovar morador | ✅ | ✅ | ❌ | ❌ |
| Listar usuários | ✅ (todos) | ✅ (próprio cond.) | ✅ (próprio cond.) | ❌ (só a si mesmo) |
| Gerenciar garagens | ✅ | ✅ | ❌ | ❌ |
| Ver garagens | ✅ | ✅ | ✅ | ✅ |
| Ver dashboard | ✅ | ✅ | ✅ | ✅ |

---

### CT-ACL-02 — Morador redireccionado ao perfil
**Pré-condição:** Login com papel `morador`
**Comportamento esperado no frontend:** Redirecionado para `/perfil` ao tentar acessar rotas protegidas

---

### CT-ACL-03 — Porteiro não vê dados de outro condomínio
**Pré-condição:** Porteiro do Condomínio A tenta `GET /api/usuarios/?condominio=2`
**Resultado esperado:** Lista retorna apenas usuários do Condomínio A (filtragem automática)

---

## Endpoints Disponíveis

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/auth/login/` | Login via CPF ou e-mail |
| `POST` | `/api/auth/refresh/` | Renovar access token |
| `POST` | `/api/auth/logout/` | Logout (blacklist do refresh token) |
| `GET/POST` | `/api/condominios/` | Listar / criar condomínios |
| `GET/PATCH/DELETE` | `/api/condominios/{id}/` | Detalhe / editar / excluir |
| `GET/POST` | `/api/usuarios/` | Listar / criar usuários |
| `GET/PATCH/DELETE` | `/api/usuarios/{id}/` | Detalhe / editar / excluir |
| `GET` | `/api/usuarios/me/` | Perfil do usuário autenticado |
| `PATCH` | `/api/usuarios/me_update/` | Atualizar próprio perfil |
| `GET` | `/api/usuarios/pendentes/` | Listar moradores pendentes |
| `PATCH` | `/api/usuarios/{id}/aprovar/` | Aprovar morador |
| `PATCH` | `/api/usuarios/{id}/rejeitar/` | Rejeitar morador |
| `GET/POST` | `/api/garagens/` | Listar / criar garagens |
| `GET/PATCH/DELETE` | `/api/garagens/{id}/` | Detalhe / editar / excluir |
| `GET` | `/api/dashboard/stats/` | Estatísticas do condomínio |
| `GET` | `/api/health/` | Health check da API |
