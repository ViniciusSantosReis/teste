.DEFAULT_GOAL := ajuda
SHELL := /bin/bash

ajuda:            ## Lista os alvos
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "};{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

setup:            ## Copia o .env e sobe a infraestrutura pela primeira vez
	@test -f .env || cp .env.example .env
	docker compose up -d --build

up:               ## Sobe todos os serviços
	docker compose up -d

down:             ## Derruba os serviços (mantém os volumes)
	docker compose down

logs:             ## Segue o log da API
	docker compose logs -f backend

shell:            ## Abre um shell no container da API
	docker compose exec backend bash

migrate:          ## Aplica as migrations
	docker compose exec backend alembic upgrade head

revision:         ## Gera uma migration:  make revision m="cria tabela setores"
	docker compose exec backend alembic revision --autogenerate -m "$(m)"

seed:             ## Popula o banco com dados de demonstração
	docker compose exec backend python -m app.seed

lint:             ## Ruff (check + format)
	docker compose exec backend ruff check app tests
	docker compose exec backend ruff format --check app tests

fix:              ## Corrige o que o Ruff sabe corrigir
	docker compose exec backend ruff check --fix app tests
	docker compose exec backend ruff format app tests

tipos:            ## mypy
	docker compose exec backend mypy app

teste:            ## pytest com cobertura
	docker compose exec backend pytest

verificar: lint tipos teste  ## O que a CI roda

backup:           ## Dump do banco para o bucket decos-backup
	bash infra/scripts/backup.sh

carga:            ## Teste de carga do RNF004 — 160 VUs, p(95) < 800 ms (sprint 11)
	k6 run --vus 160 --duration 5m -e BASE_URL=$(BASE_URL) infra/carga/rnf004.js

.PHONY: ajuda setup up down logs shell migrate revision seed lint fix tipos teste verificar backup carga
