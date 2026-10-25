// Teste de carga k6 do RNF004 — 160 VUs, p(95) < 800 ms, erro < 1%. Script na seção 6.6 do PROJETO.md.
// k6 run --vus 160 --duration 5m -e BASE_URL=... -e EMAIL=... -e SENHA=... infra/carga/rnf004.js
// Rodar contra seed de volume realista (200 mil publicações, 2 milhões de reações) — nunca contra banco vazio.
