# Intranet Decós — API

Backend da Intranet Hospitalar Decós Corporativa. FastAPI + SQLAlchemy 2.0 + Oracle 23ai,
três camadas (router → service → repository), on-premise em Docker.

> **Fonte da verdade:** [`PROJETO.md`](PROJETO.md). Stack, modelo de dados, contrato da API,
> convenções e regras de code review estão lá. Leia antes de abrir qualquer PR.

Frontend: repositório [`intranet-decos-web`](../intranet-decos-web).

## Setup

```bash
cp .env.example .env
make setup          # sobe Oracle, MinIO, Redis, GlitchTip e a API
make migrate
make seed
```

| Serviço | Endereço |
|---|---|
| API | http://localhost:8000/api/v1 |
| Documentação (OpenAPI) | http://localhost:8000/docs |
| Painel admin (sqladmin) | http://localhost:8000/admin |
| MinIO Console | http://localhost:9001 |
| GlitchTip | http://localhost:8080 |
| Oracle | localhost:1521 / FREEPDB1 |

## Estrutura

```
app/
├── main.py            monta a app, os routers e o exception_handler global
├── core/              config, db, security, permissoes, storage, imagens, logging, observability, auditoria
├── modules/           publicacoes · interacoes · documentos · diretorio · identidade
│   └── <modulo>/      models.py routers.py schemas.py services.py repositories.py
├── admin/             sqladmin
├── jobs/              APScheduler: expiração, aniversários, reconciliação
└── shared/            exceções de domínio, paginação por cursor, normalizar()
alembic/versions/      migrations
tests/                 espelha modules/
infra/                 Caddyfile, backup.sh, carga/rnf004.js (k6 — RNF004)
docs/                  arquitetura, modelo de dados, ADRs
```

## Comandos

`make ajuda` lista todos. Os que importam no dia a dia:

| Comando | O quê |
|---|---|
| `make up` / `make down` | sobe / derruba o ambiente |
| `make migrate` | `alembic upgrade head` |
| `make revision m="..."` | gera uma migration |
| `make verificar` | lint + tipos + testes (o mesmo que a CI roda) |
| `make logs` | segue o log da API |
| `make carga` | teste de carga do RNF004 (160 VUs, sprint 11) |

## Antes de abrir o PR

Rode `make verificar`. A CI bloqueia o merge em lint, tipos, testes (60% nos services),
migrations do zero e build da imagem. E releia as 10 regras da seção 11 do PROJETO.md —
`FETCH FIRST` em vez de `LIMIT`, string vazia é `NULL` no Oracle, nada de `DELETE` físico
em conteúdo, `log.info()` no lugar de `print()`.

Commits em Conventional Commits. Branches `feat/nome-curto` e `fix/nome-curto`.
PR sem revisão de outro membro não entra.
