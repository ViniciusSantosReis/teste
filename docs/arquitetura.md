# Arquitetura

> Preencher na sprint 1. Referência: seções 2, 9 e 11 do PROJETO.md.

## Visão geral
<!-- Diagrama de contêineres: React → Caddy → FastAPI → Oracle / MinIO / Redis. -->

## Três camadas e a direção da dependência
<!-- Router → Service → Repository. O que cada uma pode importar e o que nunca faz. -->

## Autenticação e sessão
<!-- Access token no estado do React, refresh em cookie httpOnly com rotação e blacklist no Redis. -->

## Upload e storage
<!-- Pipeline de imagem, buckets, convenção de chave, ordem da transação. -->

## Observabilidade
<!-- request_id, structlog JSON, GlitchTip. -->

## Permissões (RD002)
<!-- Quatro papéis: COLABORADOR, RH, MARKETING, ADMIN. Matriz declarada uma vez em
     app/core/permissoes.py e verificada por exige("acao"), nunca por if de papel no endpoint. -->

## Capacidade (RNF004)
<!-- Pico de ~160 usuários simultâneos: 4 workers do Uvicorn, pool 10 + overflow 10,
     pool_pre_ping, cache de setores e ramais no Redis, assets imutáveis no Caddy.
     Confirmar com o DBA o limite de sessões simultâneas do profile: 4 x 20 = até 80.
     Evidência de aceite: infra/carga/rnf004.js na sprint 11. Seção 6.6 do PROJETO.md. -->
