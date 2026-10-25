# Intranet Hospitalar Decós — Blueprint do Repositório

> **Como usar este arquivo.** Salve-o na raiz do repositório como `PROJETO.md` e crie um
> `CLAUDE.md` (ou `AGENTS.md`) com o conteúdo `Leia PROJETO.md antes de qualquer alteração.`
> Ele é a fonte da verdade: stack, modelo de dados, convenções e regras que não se negociam
> dentro de uma sprint. Qualquer decisão que contrarie este arquivo precisa alterá-lo no mesmo PR.

**Projeto:** Intranet Hospitalar Decós Corporativa · Hospital Decós · Setor de Tecnologia
**Contexto acadêmico:** UNIT — Universidade Tiradentes / Porto Digital · 6 meses · 12 sprints
**Equipe:** 3–5 desenvolvedores, nível júnior/pleno
**Implantação:** on-premise, Docker · **Custo de software:** R$ 0 (100% OSS)
**Backlog de referência:** `Backlog Decós.xlsx` — RF001–RF018, RD001–RD002, RNF001–RNF005

---

## Índice

1. [O produto](#1-o-produto)
2. [Stack](#2-stack)
3. [Modelo de dados — o estudo](#3-modelo-de-dados--o-estudo)
4. [DDL completo](#4-ddl-completo-oracle)
5. [Modelos SQLAlchemy](#5-modelos-sqlalchemy)
6. [Consultas críticas e índices](#6-consultas-críticas-e-índices)
7. [Fotos e arquivos](#7-fotos-e-arquivos)
8. [Moderação e permissões](#8-moderação-e-permissões)
9. [Estrutura de pastas](#9-estrutura-de-pastas)
10. [Contrato da API](#10-contrato-da-api)
11. [Convenções de código](#11-convenções-de-código)
12. [Variáveis de ambiente](#12-variáveis-de-ambiente)
13. [docker-compose](#13-docker-compose)
14. [Setup em 10 minutos](#14-setup-em-10-minutos)
15. [CI/CD](#15-cicd)
16. [Roadmap](#16-roadmap)
17. [Definition of Done](#17-definition-of-done)
18. [Lacunas do escopo original, corrigidas](#18-lacunas-do-escopo-original-corrigidas)
19. [O que este projeto NÃO vai fazer](#19-o-que-este-projeto-não-vai-fazer)

---

## 1. O produto

Uma intranet corporativa **com camada social**. A ordem dos termos importa: o eixo continua sendo
comunicação institucional (aviso, POP, ramal), e o social é o que faz o colaborador voltar todo dia.
Isso define uma regra que atravessa o sistema inteiro:

> **Conteúdo institucional e conteúdo social convivem no mesmo feed, mas não têm o mesmo peso.**
> Aviso oficial é fixável, pode exigir ciência e nunca é removido por denúncia.
> Post de colaborador é espontâneo, moderável e some se violar a política interna.

### Tipos de conteúdo

| Tipo | Quem cria | Aparece no feed | Interações |
|---|---|---|---|
| **Aviso** | MARKETING, ADMIN | Sim, com destaque | Reação, comentário, ciência |
| **Post** | Qualquer colaborador | Sim | Reação, comentário, compartilhamento |
| **Evento** | MARKETING, ADMIN | Sim + agenda própria | Reação, comentário, inscrição (v2) |
| **Documento (POP)** | ADMIN | Não — repositório próprio | Download, registro de leitura |
| **FAQ** | ADMIN | Não — base de conhecimento | Contador de visualização |

### Escala real (isto define tudo que vem abaixo)

**RNF004 fixa o número: pico de aproximadamente 160 usuários simultâneos.** É o único
requisito de capacidade do backlog, é mensurável, e é o que a seção 6.6 dimensiona e testa.

Em volume de dados: de 300 a 2.000 colaboradores cadastrados, com estimativa alta de
50 publicações/dia, 500 reações/dia e 200 comentários/dia. Em um ano: ~18 mil publicações
e ~180 mil reações.

**Isso é um banco pequeno.** Qualquer decisão que se justifique por "escala" está errada aqui.
O que importa é integridade, rastreabilidade e clareza — não throughput.

---

## 2. Stack

| Camada | Escolha | Versão alvo |
|---|---|---|
| Linguagem backend | Python | 3.12 |
| Framework | FastAPI | 0.115+ |
| ORM | SQLAlchemy | 2.0 (estilo `Mapped[]`) |
| Migrations | Alembic | 1.13+ |
| Validação | Pydantic | v2 |
| Driver Oracle | `python-oracledb` (**thin mode**, sem Instant Client) | 2.x |
| Banco (dev) | Oracle Database 23ai Free (`gvenzl/oracle-free`) | — |
| Banco (prod) | Oracle licenciado do hospital | a confirmar com o DBA |
| Storage | MinIO (S3 compatível) via `boto3` | — |
| Cache / rate limit | Redis | 7 |
| Jobs agendados | APScheduler | 3.x |
| Painel admin | `sqladmin` | — |
| Imagens | Pillow | 10+ |
| Erros | GlitchTip (SDK `sentry-sdk` / `@sentry/react`) | — |
| Logs | `structlog` (JSON) | — |
| Senha | Argon2id (`argon2-cffi` via `passlib`) | — |
| Frontend | React + Vite + TypeScript | React 19 |
| Estilo | Tailwind CSS | 4 |
| Estado de servidor | TanStack Query | v5 |
| Formulários | React Hook Form + Zod | — |
| Proxy | Caddy | 2 |
| CI | GitHub Actions | — |
| Lint/format | Ruff (Python), ESLint + Prettier (TS) | — |
| Tipos | mypy, `tsc --noEmit` | — |
| Testes | pytest, pytest-asyncio | — |

---

## 3. Modelo de dados — o estudo

### 3.1 O problema central

Com a camada social, existem **três tipos de conteúdo publicável** (aviso, post, evento) e
**quatro interações** que se aplicam a todos eles (reação, comentário, anexo, denúncia).
A forma de resolver isso é a decisão mais importante do banco inteiro — errar aqui
custa refatoração no meio do projeto.

### 3.2 As quatro alternativas

**A) Uma tabela por tipo, interações duplicadas**
`avisos`, `posts`, `eventos` + `curtidas_aviso`, `curtidas_post`, `curtidas_evento`,
`comentarios_aviso`… → 3 tipos × 4 interações = **12 tabelas de interação**.
Cada feature nova multiplica. O feed vira `UNION ALL` de três consultas com
paginação impossível de fazer certo. ❌ **Rejeitada.**

**B) Tabela única com discriminador e colunas anuláveis**
Uma `publicacoes` com `tipo` e todas as colunas de todos os tipos, a maioria `NULL`.
Interações ficam simples, mas `data_inicio` de evento não pode ser `NOT NULL`,
e o banco deixa de proteger o que deveria. Em seis meses ninguém sabe quais colunas
valem para qual tipo. ❌ **Rejeitada.**

**C) Associação polimórfica genérica** (`entidade VARCHAR2`, `entidade_id NUMBER`, sem FK)
Flexível e sedutora — e **destrói a integridade referencial**. O banco não consegue impedir
uma curtida apontando para uma publicação inexistente, e `ON DELETE CASCADE` não existe.
Aceitável **apenas** para log append-only (a tabela `auditoria`). ❌ **Rejeitada para conteúdo.**

**D) Herança por tabela juntada** *(joined table inheritance)* ✅ **ESCOLHIDA**

Uma tabela base `publicacoes` com tudo que os três tipos compartilham, e uma tabela filha por tipo
cuja chave primária **é também chave estrangeira** para a base:

```
                    ┌─────────────────────┐
                    │    publicacoes      │  ← id, tipo, autor, status, publicado_em,
                    │  (tudo em comum)    │    visibilidade, contadores, soft delete
                    └──────────┬──────────┘
              ┌────────────────┼────────────────┐
              │                │                │
        ┌─────▼─────┐   ┌──────▼─────┐   ┌──────▼─────┐
        │  avisos   │   │  eventos   │   │   posts    │
        │ prioridade│   │ data_inicio│   │ origem     │
        │ req_ciência│  │ local      │   │ (compart.) │
        └───────────┘   └────────────┘   └────────────┘

  reacoes ─┐
comentarios├──► id_publicacao ──► publicacoes.id   (FK real, uma só)
   anexos ─┤
 denuncias ┘
```

**Por que ela vence:**

- O feed é **uma única consulta** em `publicacoes` ordenada por `publicado_em`. Sem `UNION`,
  com paginação correta e um índice só. Este é o argumento decisivo: sem uma base comum,
  um feed cronológico misto é um problema difícil; com ela, é trivial.
- Reação, comentário, anexo e denúncia têm **uma FK real** para `publicacoes.id`.
  Quatro tabelas em vez de doze, e o banco garante a integridade.
- Cada tipo mantém suas colunas obrigatórias como `NOT NULL` de verdade.
  `eventos.data_inicio NOT NULL` funciona; na alternativa B, não funcionaria.
- Adicionar um quarto tipo (enquete, vaga interna, classificados) é **uma tabela nova**,
  e ele já nasce com feed, reação, comentário, anexo, moderação e auditoria.
- O SQLAlchemy suporta isso nativamente com ~4 linhas por classe
  (`__mapper_args__` com `polymorphic_on` / `polymorphic_identity`).

**O custo, dito com honestidade:** ler um aviso específico faz um `JOIN` entre `publicacoes` e
`avisos`. Com ~18 mil linhas/ano e chave primária indexada, isso é irrelevante — mas a equipe
precisa entender o mapeamento antes de escrever o primeiro repository. Reserve uma sessão de
pareamento na sprint 1 para isso; é o único conceito não-óbvio do modelo inteiro.

### 3.3 O que ficou fora da hierarquia, de propósito

**`documentos` (POPs) não é uma `publicacao`.** É um agregado diferente: tem código
institucional (`POP-ENF-014`), versão vigente, histórico de revisões e registro de leitura.
Não vive no feed, não recebe curtida, e sua exclusão é assunto de compliance, não de moderação.
Forçá-lo na hierarquia contaminaria os dois modelos.

**`faq` também não.** É base de conhecimento com ordenação manual, sem autor social, sem feed.

Um aviso *pode referenciar* um documento (`anexos` com `tipo='ARQUIVO'` ou link no corpo) —
mas são entidades distintas.

### 3.4 Decisões de modelagem, uma a uma

| Decisão | Escolha | Por quê |
|---|---|---|
| **Exclusão** | Soft delete (`excluido_em`) em todo conteúdo | Requisito "não perder informação". A API expõe *arquivar*, nunca `DELETE` físico. Purga real só por job de retenção após 90 dias na lixeira. |
| **Reações** | Uma linha por (publicação, usuário) com `UNIQUE`, e coluna `tipo` já presente | A constraint `UNIQUE` é o que impede curtida dupla — **não confie no frontend**. A coluna `tipo` nasce com `'CURTIR'`; se quiserem 👏 e ❤️ na v2, é dado novo, não migration de schema. |
| **Contadores** | Desnormalizados em `publicacoes` (`curtidas_total`, `comentarios_total`) | `COUNT(*)` por publicação em cada scroll do feed é o gargalo clássico. Atualizados por `UPDATE ... SET x = x + 1` na mesma transação, com job noturno de reconciliação. |
| **Comentários** | Um nível de resposta (`id_comentario_pai`), não árvore livre | Árvore recursiva exige `CONNECT BY`/CTE e complica a UI. Um nível cobre 99% do uso real e é o que Instagram e LinkedIn fazem. |
| **Visualizações** | Contador agregado para posts; **linha por usuário só para POP e aviso com ciência** | Uma linha por visualização de feed cresce sem limite e não serve para nada. Já saber *quem leu o POP de higienização* é exigência de auditoria hospitalar. |
| **Anexos** | Tabela própria com ordem, nunca coluna de URL | Post com 5 fotos precisa de carrossel ordenado. E o banco guarda **coordenada de objeto** (`bucket` + `object_key` + `version_id`), nunca URL — se o MinIO mudar de host, nada quebra. |
| **Aniversariantes** | Colunas virtuais `nasc_mes` / `nasc_dia` com índice | `WHERE EXTRACT(MONTH FROM data_nascimento) = :mes` não usa índice. Coluna virtual do Oracle (`Computed()` no SQLAlchemy) resolve, ocupa zero byte e funciona igual no Postgres. |
| **Busca** | Coluna derivada `*_busca` (minúscula, sem acento) com índice | Oracle Text pode não estar instalado na instância do hospital. A coluna derivada funciona em qualquer versão e é preenchida no service. |
| **Visibilidade** | `PUBLICO` ou `SETOR` | Suficiente para o MVP. Grupos e listas de distribuição ficam para a v2. |
| **Auditoria** | Tabela append-only com `diff` em JSON, alimentada por evento SQLAlchemy | Nunca por chamada manual — chamada manual é esquecida. É o único lugar onde referência polimórfica é aceitável. |

---

## 4. DDL completo (Oracle)

> Este DDL é a **referência**. Na prática ele é gerado por `alembic revision --autogenerate`
> a partir dos modelos da seção 5 e depois **revisado à mão**.
> `Base.metadata.create_all()` é proibido em qualquer ambiente, inclusive testes.

### 4.1 Fundação

```sql
CREATE TABLE setores (
    id            NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    nome          VARCHAR2(100) NOT NULL,
    nome_busca    VARCHAR2(100) NOT NULL,
    sigla         VARCHAR2(15),
    ramal_geral   VARCHAR2(10),
    andar         VARCHAR2(20),                      -- lacuna do escopo original
    bloco         VARCHAR2(20),
    ativo         NUMBER(1) DEFAULT 1 NOT NULL,
    criado_em     TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT uq_setores_nome UNIQUE (nome)
);
CREATE INDEX ix_setores_andar ON setores (andar, bloco);

CREATE TABLE usuarios (
    id                NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    nome              VARCHAR2(150) NOT NULL,
    nome_busca        VARCHAR2(150) NOT NULL,
    email             VARCHAR2(150) NOT NULL,
    senha_hash        VARCHAR2(255) NOT NULL,        -- Argon2id cabe folgado
    id_setor          NUMBER REFERENCES setores(id),
    cargo             VARCHAR2(100),
    ramal             VARCHAR2(10),                  -- ramal individual (lacuna do escopo)
    data_nascimento   DATE,
    data_admissao     DATE,
    bio               VARCHAR2(300),
    foto_object_key   VARCHAR2(1024),
    role              VARCHAR2(15) DEFAULT 'COLABORADOR' NOT NULL,
    ativo             NUMBER(1) DEFAULT 1 NOT NULL,
    desligado_em      TIMESTAMP WITH TIME ZONE,
    ultimo_login_em   TIMESTAMP WITH TIME ZONE,
    criado_em         TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em     TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_usuarios_email UNIQUE (email),
    CONSTRAINT ck_usuarios_role  CHECK (role IN ('COLABORADOR','RH','MARKETING','ADMIN'))
);

-- Colunas virtuais: custo zero de armazenamento, e tornam a busca de
-- aniversariantes indexável. Equivalente a Computed() no SQLAlchemy.
ALTER TABLE usuarios ADD (
    nasc_mes NUMBER(2) GENERATED ALWAYS AS (EXTRACT(MONTH FROM data_nascimento)) VIRTUAL,
    nasc_dia NUMBER(2) GENERATED ALWAYS AS (EXTRACT(DAY   FROM data_nascimento)) VIRTUAL
);
CREATE INDEX ix_usuarios_aniversario ON usuarios (nasc_mes, nasc_dia);
CREATE INDEX ix_usuarios_setor       ON usuarios (id_setor, ativo);
CREATE INDEX ix_usuarios_busca       ON usuarios (nome_busca);

CREATE TABLE categorias (
    id     NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    nome   VARCHAR2(100) NOT NULL,
    slug   VARCHAR2(120) NOT NULL,
    tipo   VARCHAR2(15)  NOT NULL,                   -- PUBLICACAO | DOCUMENTO | FAQ
    cor    VARCHAR2(7),                              -- #0F6E78, para o chip na UI
    ordem  NUMBER DEFAULT 0 NOT NULL,
    ativo  NUMBER(1) DEFAULT 1 NOT NULL,
    CONSTRAINT uq_categorias_slug UNIQUE (slug, tipo),
    CONSTRAINT ck_categorias_tipo CHECK (tipo IN ('PUBLICACAO','DOCUMENTO','FAQ'))
);
```

### 4.2 Hierarquia de publicações

```sql
CREATE TABLE publicacoes (
    id                  NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    tipo                VARCHAR2(10) NOT NULL,       -- discriminador da herança
    id_autor            NUMBER NOT NULL REFERENCES usuarios(id),
    id_setor            NUMBER REFERENCES setores(id),
    id_categoria        NUMBER REFERENCES categorias(id),
    titulo              VARCHAR2(200),               -- anulável: post pode não ter título
    titulo_busca        VARCHAR2(200),
    corpo               CLOB,
    status              VARCHAR2(12) DEFAULT 'RASCUNHO' NOT NULL,
    visibilidade        VARCHAR2(10) DEFAULT 'PUBLICO'  NOT NULL,
    fixado              NUMBER(1) DEFAULT 0 NOT NULL,
    permite_comentario  NUMBER(1) DEFAULT 1 NOT NULL,
    publicado_em        TIMESTAMP WITH TIME ZONE,
    expira_em           TIMESTAMP WITH TIME ZONE,
    reacoes_total       NUMBER DEFAULT 0 NOT NULL,
    comentarios_total   NUMBER DEFAULT 0 NOT NULL,
    criado_em           TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em       TIMESTAMP WITH TIME ZONE,
    excluido_em         TIMESTAMP WITH TIME ZONE,
    CONSTRAINT ck_pub_tipo   CHECK (tipo IN ('AVISO','POST','EVENTO')),
    CONSTRAINT ck_pub_status CHECK (status IN ('RASCUNHO','PUBLICADO','EM_REVISAO','ARQUIVADO','REMOVIDO')),
    CONSTRAINT ck_pub_visib  CHECK (visibilidade IN ('PUBLICO','SETOR'))
);

-- Índice do feed. A ordem das colunas é deliberada: igualdade primeiro,
-- ordenação depois. É o índice mais importante do sistema.
CREATE INDEX ix_pub_feed   ON publicacoes (status, publicado_em DESC, id DESC);
CREATE INDEX ix_pub_autor  ON publicacoes (id_autor, publicado_em DESC);
CREATE INDEX ix_pub_setor  ON publicacoes (id_setor, status, publicado_em DESC);
CREATE INDEX ix_pub_busca  ON publicacoes (titulo_busca);
CREATE INDEX ix_pub_lixeira ON publicacoes (excluido_em);

CREATE TABLE avisos (
    id              NUMBER PRIMARY KEY REFERENCES publicacoes(id),
    prioridade      VARCHAR2(10) DEFAULT 'NORMAL' NOT NULL,
    requer_ciencia  NUMBER(1) DEFAULT 0 NOT NULL,
    CONSTRAINT ck_avisos_prioridade CHECK (prioridade IN ('NORMAL','ALTA','URGENTE'))
);

CREATE TABLE eventos (
    id                 NUMBER PRIMARY KEY REFERENCES publicacoes(id),
    data_inicio        TIMESTAMP WITH TIME ZONE NOT NULL,   -- NOT NULL de verdade
    data_fim           TIMESTAMP WITH TIME ZONE,
    local              VARCHAR2(150),
    vagas              NUMBER,
    permite_inscricao  NUMBER(1) DEFAULT 0 NOT NULL,
    CONSTRAINT ck_eventos_periodo CHECK (data_fim IS NULL OR data_fim >= data_inicio)
);
CREATE INDEX ix_eventos_agenda ON eventos (data_inicio);

CREATE TABLE posts (
    id                    NUMBER PRIMARY KEY REFERENCES publicacoes(id),
    id_publicacao_origem  NUMBER REFERENCES publicacoes(id)   -- compartilhamento
);
```

### 4.3 Interações sociais

```sql
CREATE TABLE reacoes (
    id             NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_publicacao  NUMBER NOT NULL REFERENCES publicacoes(id) ON DELETE CASCADE,
    id_usuario     NUMBER NOT NULL REFERENCES usuarios(id),
    tipo           VARCHAR2(12) DEFAULT 'CURTIR' NOT NULL,
    criado_em      TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    -- É esta constraint que impede curtida dupla. Não o frontend.
    CONSTRAINT uq_reacoes UNIQUE (id_publicacao, id_usuario),
    CONSTRAINT ck_reacoes_tipo CHECK (tipo IN ('CURTIR','PARABENS','APOIO'))
);

CREATE TABLE comentarios (
    id                 NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_publicacao      NUMBER NOT NULL REFERENCES publicacoes(id) ON DELETE CASCADE,
    id_usuario         NUMBER NOT NULL REFERENCES usuarios(id),
    id_comentario_pai  NUMBER REFERENCES comentarios(id),   -- um nível apenas
    corpo              VARCHAR2(2000) NOT NULL,
    criado_em          TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em      TIMESTAMP WITH TIME ZONE,
    excluido_em        TIMESTAMP WITH TIME ZONE
);
CREATE INDEX ix_comentarios_pub ON comentarios (id_publicacao, criado_em);

CREATE TABLE anexos (
    id                 NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_publicacao      NUMBER NOT NULL REFERENCES publicacoes(id) ON DELETE CASCADE,
    tipo               VARCHAR2(10) NOT NULL,               -- IMAGEM | ARQUIVO
    bucket             VARCHAR2(63)   NOT NULL,
    object_key         VARCHAR2(1024) NOT NULL,             -- original
    object_key_medio   VARCHAR2(1024),                      -- 1080px, WebP
    object_key_thumb   VARCHAR2(1024),                      -- 320px, WebP
    version_id         VARCHAR2(128),
    nome_original      VARCHAR2(255),
    mime_type          VARCHAR2(120),
    tamanho_bytes      NUMBER,
    checksum_sha256    VARCHAR2(64),
    largura            NUMBER,
    altura             NUMBER,
    legenda            VARCHAR2(300),
    ordem              NUMBER DEFAULT 0 NOT NULL,           -- carrossel
    criado_em          TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT ck_anexos_tipo CHECK (tipo IN ('IMAGEM','ARQUIVO'))
);
CREATE INDEX ix_anexos_pub ON anexos (id_publicacao, ordem);

-- "Li e estou ciente" — para aviso institucional que exige confirmação.
CREATE TABLE ciencias (
    id_publicacao  NUMBER NOT NULL REFERENCES publicacoes(id),
    id_usuario     NUMBER NOT NULL REFERENCES usuarios(id),
    ciente_em      TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT pk_ciencias PRIMARY KEY (id_publicacao, id_usuario)
);

CREATE TABLE denuncias (
    id             NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_publicacao  NUMBER REFERENCES publicacoes(id),
    id_comentario  NUMBER REFERENCES comentarios(id),
    id_denunciante NUMBER NOT NULL REFERENCES usuarios(id),
    motivo         VARCHAR2(30)  NOT NULL,
    detalhe        VARCHAR2(500),
    status         VARCHAR2(12) DEFAULT 'ABERTA' NOT NULL,
    id_moderador   NUMBER REFERENCES usuarios(id),
    resolvido_em   TIMESTAMP WITH TIME ZONE,
    criado_em      TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT ck_denuncias_alvo   CHECK (
        (id_publicacao IS NOT NULL AND id_comentario IS NULL) OR
        (id_publicacao IS NULL AND id_comentario IS NOT NULL)),
    CONSTRAINT ck_denuncias_status CHECK (status IN ('ABERTA','PROCEDENTE','IMPROCEDENTE'))
);
CREATE INDEX ix_denuncias_fila ON denuncias (status, criado_em);

CREATE TABLE notificacoes (
    id              NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_destinatario NUMBER NOT NULL REFERENCES usuarios(id),
    id_ator         NUMBER REFERENCES usuarios(id),
    tipo            VARCHAR2(20) NOT NULL,
    id_publicacao   NUMBER REFERENCES publicacoes(id) ON DELETE CASCADE,
    id_comentario   NUMBER REFERENCES comentarios(id) ON DELETE CASCADE,
    lida_em         TIMESTAMP WITH TIME ZONE,
    criado_em       TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT ck_notif_tipo CHECK (tipo IN
        ('REACAO','COMENTARIO','RESPOSTA','AVISO_OFICIAL','ANIVERSARIO','MODERACAO'))
);
CREATE INDEX ix_notif_caixa ON notificacoes (id_destinatario, lida_em, criado_em DESC);
```

### 4.4 Documentos, FAQ e auditoria

```sql
CREATE TABLE documentos (
    id                     NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    codigo                 VARCHAR2(50) NOT NULL,          -- POP-ENF-014
    titulo                 VARCHAR2(200) NOT NULL,
    titulo_busca           VARCHAR2(200) NOT NULL,
    descricao              VARCHAR2(1000),
    id_categoria           NUMBER REFERENCES categorias(id),
    id_setor_responsavel   NUMBER REFERENCES setores(id),
    versao_vigente         NUMBER,
    requer_leitura         NUMBER(1) DEFAULT 0 NOT NULL,
    criado_em              TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em          TIMESTAMP WITH TIME ZONE,
    excluido_em            TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_documentos_codigo UNIQUE (codigo)
);
CREATE INDEX ix_documentos_busca ON documentos (titulo_busca);

-- POP hospitalar é documento controlado: o histórico de versões é requisito,
-- não conveniência. O versionamento do MinIO guarda o arquivo; esta tabela
-- guarda o significado (versão 3, vigente desde 01/2026, publicada por Fulano).
CREATE TABLE documento_versoes (
    id               NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    id_documento     NUMBER NOT NULL REFERENCES documentos(id),
    numero           NUMBER NOT NULL,
    bucket           VARCHAR2(63)   NOT NULL,
    object_key       VARCHAR2(1024) NOT NULL,
    version_id       VARCHAR2(128),
    mime_type        VARCHAR2(120),
    tamanho_bytes    NUMBER,
    checksum_sha256  VARCHAR2(64),
    notas_revisao    VARCHAR2(1000),
    id_uploader      NUMBER NOT NULL REFERENCES usuarios(id),
    vigente_desde    TIMESTAMP WITH TIME ZONE,
    criado_em        TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT uq_doc_versao UNIQUE (id_documento, numero)
);

CREATE TABLE documento_leituras (
    id_documento  NUMBER NOT NULL REFERENCES documentos(id),
    id_versao     NUMBER NOT NULL REFERENCES documento_versoes(id),
    id_usuario    NUMBER NOT NULL REFERENCES usuarios(id),
    lido_em       TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT pk_doc_leituras PRIMARY KEY (id_documento, id_versao, id_usuario)
);

CREATE TABLE faq (
    id              NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    pergunta        VARCHAR2(300) NOT NULL,
    pergunta_busca  VARCHAR2(300) NOT NULL,
    resposta        CLOB NOT NULL,
    id_categoria    NUMBER REFERENCES categorias(id),
    ordem           NUMBER DEFAULT 0 NOT NULL,
    visualizacoes   NUMBER DEFAULT 0 NOT NULL,
    criado_em       TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    atualizado_em   TIMESTAMP WITH TIME ZONE,
    excluido_em     TIMESTAMP WITH TIME ZONE
);
CREATE INDEX ix_faq_busca ON faq (pergunta_busca);

-- Append-only. Único lugar onde referência polimórfica é aceitável,
-- porque é log histórico e a linha referenciada pode não existir mais.
CREATE TABLE auditoria (
    id           NUMBER GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    entidade     VARCHAR2(40) NOT NULL,
    entidade_id  NUMBER       NOT NULL,
    acao         VARCHAR2(15) NOT NULL,
    id_usuario   NUMBER REFERENCES usuarios(id),
    request_id   VARCHAR2(36),                 -- amarra com o log e com o GlitchTip
    ip_origem    VARCHAR2(45),
    diff         CLOB,                         -- {"campo": ["antes", "depois"]}
    ocorrido_em  TIMESTAMP WITH TIME ZONE DEFAULT SYSTIMESTAMP NOT NULL,
    CONSTRAINT ck_auditoria_acao CHECK (acao IN
        ('CRIOU','ALTEROU','EXCLUIU','PUBLICOU','MODEROU','LOGIN','LOGIN_FALHA'))
);
CREATE INDEX ix_auditoria_entidade ON auditoria (entidade, entidade_id, ocorrido_em DESC);
CREATE INDEX ix_auditoria_usuario  ON auditoria (id_usuario, ocorrido_em DESC);
```

---

## 5. Modelos SQLAlchemy

### 5.1 Base e mixins — `app/core/db.py`

```python
from datetime import datetime
from sqlalchemy import MetaData, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declarative_mixin

# Sem isso, o Alembic gera nomes de constraint que estouram o limite do Oracle.
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


@declarative_mixin
class TimestampMixin:
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now())


@declarative_mixin
class SoftDeleteMixin:
    """Nada é apagado. O repositório filtra excluido_em IS NULL por padrão."""
    excluido_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True)

    @property
    def ativo(self) -> bool:
        return self.excluido_em is None
```

### 5.2 A hierarquia — `app/modules/publicacoes/models.py`

```python
from datetime import datetime
from sqlalchemy import (Boolean, ForeignKey, Identity, Integer, String, Text,
                        DateTime, CheckConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, SoftDeleteMixin


class Publicacao(Base, TimestampMixin, SoftDeleteMixin):
    """Base da herança por tabela juntada. É o que o feed consulta."""
    __tablename__ = "publicacoes"

    id: Mapped[int] = mapped_column(Identity(always=False), primary_key=True)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)

    id_autor: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    id_setor: Mapped[int | None] = mapped_column(ForeignKey("setores.id"))
    id_categoria: Mapped[int | None] = mapped_column(ForeignKey("categorias.id"))

    titulo: Mapped[str | None] = mapped_column(String(200))
    titulo_busca: Mapped[str | None] = mapped_column(String(200), index=True)
    corpo: Mapped[str | None] = mapped_column(Text)           # CLOB no Oracle

    status: Mapped[str] = mapped_column(String(12), default="RASCUNHO", index=True)
    visibilidade: Mapped[str] = mapped_column(String(10), default="PUBLICO")
    fixado: Mapped[bool] = mapped_column(Boolean, default=False)
    permite_comentario: Mapped[bool] = mapped_column(Boolean, default=True)

    publicado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    expira_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    reacoes_total: Mapped[int] = mapped_column(Integer, default=0)
    comentarios_total: Mapped[int] = mapped_column(Integer, default=0)

    autor = relationship("Usuario", lazy="joined")
    anexos = relationship("Anexo", cascade="all, delete-orphan",
                          order_by="Anexo.ordem", lazy="selectin")

    # As 3 linhas que fazem a herança funcionar:
    __mapper_args__ = {
        "polymorphic_on": tipo,
        "polymorphic_identity": "PUBLICACAO",
        "with_polymorphic": "*",
    }


class Aviso(Publicacao):
    __tablename__ = "avisos"

    id: Mapped[int] = mapped_column(ForeignKey("publicacoes.id"), primary_key=True)
    prioridade: Mapped[str] = mapped_column(String(10), default="NORMAL")
    requer_ciencia: Mapped[bool] = mapped_column(Boolean, default=False)

    __mapper_args__ = {"polymorphic_identity": "AVISO"}


class Evento(Publicacao):
    __tablename__ = "eventos"

    id: Mapped[int] = mapped_column(ForeignKey("publicacoes.id"), primary_key=True)
    data_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_fim: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    local: Mapped[str | None] = mapped_column(String(150))
    vagas: Mapped[int | None] = mapped_column(Integer)
    permite_inscricao: Mapped[bool] = mapped_column(Boolean, default=False)

    __mapper_args__ = {"polymorphic_identity": "EVENTO"}


class Post(Publicacao):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(ForeignKey("publicacoes.id"), primary_key=True)
    id_publicacao_origem: Mapped[int | None] = mapped_column(ForeignKey("publicacoes.id"))

    __mapper_args__ = {
        "polymorphic_identity": "POST",
        # necessário: posts tem duas FKs para publicacoes (herança + compartilhamento)
        "inherit_condition": id == Publicacao.id,
    }
```

### 5.3 Colunas virtuais — `app/modules/identidade/models.py`

```python
from datetime import date
from sqlalchemy import Computed, Date, Integer, String
from sqlalchemy.orm import Mapped, mapped_column


class Usuario(Base, TimestampMixin):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Identity(always=False), primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    nome_busca: Mapped[str] = mapped_column(String(150), index=True)
    email: Mapped[str] = mapped_column(String(150), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    data_nascimento: Mapped[date | None] = mapped_column(Date)

    # Coluna virtual do Oracle: não ocupa espaço, é indexável e resolve
    # "aniversariantes do mês" sem varrer a tabela inteira.
    nasc_mes: Mapped[int | None] = mapped_column(
        Integer, Computed("EXTRACT(MONTH FROM data_nascimento)"))
    nasc_dia: Mapped[int | None] = mapped_column(
        Integer, Computed("EXTRACT(DAY FROM data_nascimento)"))

    role: Mapped[str] = mapped_column(String(15), default="COLABORADOR")
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
```

---

## 6. Consultas críticas e índices

### 6.1 Feed — paginação por cursor, nunca por OFFSET

`OFFSET 200 ROWS` obriga o banco a ler e descartar 200 linhas, e — pior — em rolagem infinita
duplica ou pula itens sempre que alguém publica algo durante a navegação. Use **keyset pagination**:

```python
stmt = (
    select(Publicacao)
    .where(
        Publicacao.status == "PUBLICADO",
        Publicacao.excluido_em.is_(None),
        or_(
            Publicacao.visibilidade == "PUBLICO",
            Publicacao.id_setor == usuario.id_setor,
        ),
    )
    .order_by(Publicacao.publicado_em.desc(), Publicacao.id.desc())
    .limit(20)
)

if cursor:  # cursor = (publicado_em, id) do último item da página anterior
    c_data, c_id = cursor
    # ATENÇÃO: o Oracle NÃO aceita comparação de tupla — (a, b) < (c, d) não existe.
    # Precisa ser escrito na forma expandida:
    stmt = stmt.where(
        or_(
            Publicacao.publicado_em < c_data,
            and_(Publicacao.publicado_em == c_data, Publicacao.id < c_id),
        )
    )
```

Fixados vêm em consulta separada (`WHERE fixado = 1`), no topo, fora da paginação.

### 6.2 Aniversariantes do mês

```python
# Com as colunas virtuais, isso usa ix_usuarios_aniversario.
select(Usuario).where(Usuario.nasc_mes == mes, Usuario.ativo.is_(True)) \
               .order_by(Usuario.nasc_dia)
```

A resposta da API devolve **dia e mês, nunca o ano.** Não há razão de negócio para expor a
idade de um colaborador ao hospital inteiro, e isso é dado pessoal sob a LGPD.

### 6.3 Contadores — incremento atômico, não leitura-e-escrita

```python
# Correto: uma instrução, sem condição de corrida.
await session.execute(
    update(Publicacao)
    .where(Publicacao.id == pub_id)
    .values(reacoes_total=Publicacao.reacoes_total + 1)
)

# ERRADO: dois usuários curtindo ao mesmo tempo perdem uma curtida.
# pub.reacoes_total = pub.reacoes_total + 1
```

Job noturno de reconciliação corrige qualquer desvio comparando com `COUNT(*)` real.

### 6.4 Busca sem acento

Normalize no service e grave na coluna `*_busca`; a consulta usa a coluna normalizada:

```python
import unicodedata

def normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode()
    return sem_acento.lower().strip()
```

### 6.5 Evitar N+1

Toda listagem que mostra autor e anexos usa `selectinload`/`joined`. Ligue
`echo=True` em desenvolvimento uma vez por sprint e olhe o número de queries do feed:
deve ser 3, não 61.

### 6.6 Capacidade — dimensionamento do RNF004

> **RNF004 — o sistema deve suportar um pico de aproximadamente 160 usuários simultâneos.**

**Traduzindo o requisito.** 160 simultâneos não é 160 requisições por segundo. Intranet é
leitura-pesada: o colaborador abre o feed, lê, busca um ramal e sai. Em regime, 160 sessões
ativas geram algo entre **15 e 30 req/s**. O que dimensiona o sistema é a rajada — 8h da manhã,
troca de plantão, todo mundo abrindo o feed ao mesmo tempo: aí o pico chega a
**80–120 req/s por alguns segundos**. Projete para a rajada, não para o regime.

**Configuração que atende.**

| Parâmetro | Valor | Motivo |
|---|---|---|
| Workers do Uvicorn | `--workers 4` em produção | Regra: 2 × vCPU, mínimo 4. Um processo só serializa a rajada. |
| `DB_POOL_SIZE` | 10 | 5 era número de protótipo; com 160 sessões e 4 workers, insuficiente. |
| `DB_MAX_OVERFLOW` | 10 | Absorve a rajada sem manter conexão ociosa aberta. |
| `pool_pre_ping` | `True` | O Oracle derruba sessão ociosa; sem isso, a primeira requisição depois do vale falha. |
| `pool_recycle` | 1800 s | Precisa ser **menor** que o `IDLE_TIME` do profile Oracle. |
| Cache no Redis | setores e ramais, TTL 10 min | São as consultas mais repetidas e as que menos mudam (RF006, RF007). |
| Caddy | compressão + `Cache-Control: immutable` nos assets | Tira do backend a maior parte das requisições da rajada. |

**Isto precisa ser confirmado com o DBA:** 4 workers × (10 + 10) = **até 80 sessões simultâneas
no Oracle**. Se o profile da conta da aplicação limitar abaixo disso, a rajada falha com erro de
conexão — não com lentidão, que seria mais fácil de diagnosticar. É a pergunta sobre sessões
simultâneas da lista para o DBA, e com o RNF004 ela deixa de ser opcional.

**O que já garante o desempenho,** e é por isso que o resto do blueprint importa aqui: a
paginação por cursor tem custo constante independente do tamanho da tabela; os contadores
desnormalizados eliminam o `COUNT(*)` por publicação a cada scroll; e as fotos são servidas
direto do MinIO por URL pré-assinada, sem passar pelo processo Python.

**Critério de aceite.** O RNF004 só é atendido com evidência medida. Script em
`infra/carga/rnf004.js`, executado na sprint 11:

```javascript
// k6 run --vus 160 --duration 5m infra/carga/rnf004.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  scenarios: { regime: { executor: 'constant-vus', vus: 160, duration: '5m' } },
  thresholds: {
    http_req_duration: ['p(95)<800'],   // 95% das respostas abaixo de 800 ms
    http_req_failed:   ['rate<0.01'],   // menos de 1% de erro
  },
};

export default function () {
  const base = __ENV.BASE_URL;

  http.post(`${base}/auth/login`,
            JSON.stringify({ email: __ENV.EMAIL, senha: __ENV.SENHA }),
            { headers: { 'Content-Type': 'application/json' } });

  const feed = http.get(`${base}/feed`);
  check(feed, { 'feed 200': r => r.status === 200 });
  sleep(3);                                          // o usuário lê

  http.get(`${base}/colaboradores?busca=silva`);      // RF005
  sleep(2);
  http.get(`${base}/documentos?busca=higienizacao`);  // RF002
  sleep(5);
}
```

Rode contra um banco com **volume realista** — 200 mil publicações e 2 milhões de reações no
seed —, nunca contra o banco vazio de desenvolvimento. Teste de carga em tabela vazia não
mede nada além da velocidade do laço.

**Se falhar, a ordem de investigação é sempre esta:** (1) índice ausente, (2) consulta N+1,
(3) número de workers, (4) tamanho do pool. Nunca comece por pedir mais hardware — em
praticamente todo caso de intranet lenta, a causa está nos dois primeiros.


---

## 7. Fotos e arquivos

### 7.1 Buckets

| Bucket | Conteúdo | Versionamento | Expiração da URL |
|---|---|---|---|
| `decos-midia` | fotos de post, imagens de aviso e evento | ligado | 60 min |
| `decos-documentos` | POPs, normas, formulários | ligado + Object Lock opcional | 5 min |
| `decos-avatares` | foto de perfil (dado pessoal) | ligado | 15 min |
| `decos-backup` | dumps do banco | ligado + retenção 90 dias | conta de serviço |

Nenhum bucket é público. Todo acesso passa por URL pré-assinada gerada **depois** de
o FastAPI validar login e permissão.

### 7.2 Convenção de chave

```
midia/publicacoes/{id_publicacao}/{uuid4}.webp
midia/publicacoes/{id_publicacao}/{uuid4}_medio.webp
midia/publicacoes/{id_publicacao}/{uuid4}_thumb.webp
documentos/{ano}/{id_categoria}/{uuid4}.pdf
avatares/{id_usuario}.webp
```

O nome original do arquivo vai em **metadado do objeto e na coluna `nome_original`** —
nunca no caminho. Dois setores enviam `POP.pdf` no mesmo dia.

### 7.3 Pipeline de upload de imagem

1. **Validar o conteúdo, não a extensão** — `python-magic` nos primeiros bytes.
2. **Teto de 10 MB por imagem** (25 MB para documento), verificado por *streaming*.
   Não carregue o arquivo inteiro na memória do Uvicorn.
3. **Remover EXIF.** Foto tirada dentro do hospital carrega GPS, modelo do aparelho e,
   às vezes, o nome do dono. Isto é requisito de LGPD, não otimização:
   ```python
   img = ImageOps.exif_transpose(Image.open(arquivo))   # respeita a rotação
   img = img.convert("RGB")                              # descarta todo o resto
   ```
4. **Gerar três variantes** — original (reencodada em WebP q=82), média (1080px) e thumb (320px).
   O feed carrega thumb; abrir a foto carrega a média; a original só em download.
5. **Enviar ao MinIO** com `ChecksumAlgorithm="SHA256"` e gravar as chaves em `anexos`.
6. **Ordem da transação:** grave os objetos **antes** do commit no banco e, se o commit falhar,
   remova os objetos no `except`. Objeto órfão é recuperável por job de limpeza; linha
   apontando para arquivo inexistente aparece como erro na cara do usuário.

### 7.4 Backup 3-2-1

| O quê | Como | Frequência | Retenção |
|---|---|---|---|
| Banco | `expdp` (Data Pump), comprimido, para `decos-backup` | diário, 02h | 7 diários · 4 semanais · 12 mensais |
| Bucket | `mc mirror --watch` para disco secundário | contínuo | espelho + versões |
| Cópia externa | `mc mirror` para Backblaze B2 (10 GB grátis) ou HD da TI | semanal | 4 semanas |
| **Teste de restauração** | restaurar num container descartável e rodar a suíte contra ele | **mensal** | evidência na ata da sprint |

Backup que nunca foi restaurado não é backup.

---

## 8. Moderação e permissões

### 8.1 Matriz de permissões

Os papéis vêm dos atores nomeados no backlog — **RD002** ("as rotas de administração devem ser
restritas conforme os privilégios dos atores: RH, Marketing, Administrador") e **RF016**
("gerenciamento de usuários… Administrador e RH"). São quatro, e são funcionais por
departamento, não níveis hierárquicos: RH não publica aviso, Marketing não mexe em usuário.

| Ação | COLABORADOR | RH | MARKETING | ADMIN | Requisito |
|---|:--:|:--:|:--:|:--:|---|
| Ler feed, POPs, FAQ, ramais, colaboradores | ✅ | ✅ | ✅ | ✅ | RF002–RF011 |
| Criar post, comentar, reagir | ✅ | ✅ | ✅ | ✅ | — |
| Editar/arquivar conteúdo próprio | ✅ | ✅ | ✅ | ✅ | — |
| Denunciar publicação ou comentário | ✅ | ✅ | ✅ | ✅ | — |
| Gerenciar avisos do mural | — | — | ✅ | ✅ | RF012 |
| Gerenciar eventos | — | — | ✅ | ✅ | RF013 |
| Fixar publicação | — | — | ✅ | ✅ | RF008 |
| Gerenciar categorias | — | — | ✅ | ✅ | — |
| Gerenciar setores | — | ✅ | — | ✅ | RF014 |
| Gerenciar ramais | — | ✅ | — | ✅ | RF015 |
| Gerenciar usuários (dados, setor, cargo) | — | ✅ | — | ✅ | RF016 |
| Gerenciar FAQ | — | — | — | ✅ | RF017 |
| Publicar POP e nova versão | — | — | — | ✅ | RF018 |
| Resolver denúncia, remover conteúdo alheio | — | — | — | ✅ | — |
| Definir o papel de um usuário | — | — | — | ✅ | RD002 |

### 8.2 Como verificar — permissão, não papel

Com quatro papéis e ações compartilhadas entre eles (RH **e** ADMIN gerenciam usuários),
checar papel no endpoint produz `if role in ("RH", "ADMIN")` espalhado pelo código — e no dia
em que um quinto papel surgir, alguém esquece um lugar. Declare a matriz **uma vez**, em dados:

```python
# app/core/permissoes.py
PERMISSOES: dict[str, set[str]] = {
    "COLABORADOR": {"conteudo:criar", "conteudo:proprio", "denuncia:criar"},
    "RH":          {"conteudo:criar", "conteudo:proprio", "denuncia:criar",
                    "setor:gerenciar", "ramal:gerenciar", "usuario:gerenciar"},
    "MARKETING":   {"conteudo:criar", "conteudo:proprio", "denuncia:criar",
                    "aviso:gerenciar", "evento:gerenciar", "publicacao:fixar",
                    "categoria:gerenciar"},
    "ADMIN":       {"*"},
}


def exige(permissao: str):
    def _dep(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        concedidas = PERMISSOES.get(usuario.role, set())
        if "*" not in concedidas and permissao not in concedidas:
            raise PermissaoNegada(permissao)
        return usuario
    return Depends(_dep)
```

```python
# uso no router — legível e testável
@router.post("/avisos", dependencies=[exige("aviso:gerenciar")])
async def criar_aviso(...): ...
```

Um teste parametrizado sobre `PERMISSOES` cobre a matriz inteira e é a evidência de aceite
do RD002. Acrescentar um papel passa a ser uma linha no dicionário, não uma caçada no código.

### 8.3 Fluxo de moderação

**Pós-moderação por padrão:** o post do colaborador é publicado na hora. É o modelo que
mantém a rede viva; pré-moderação mata o engajamento em duas semanas.

```
post criado ──► PUBLICADO
                   │
                   ├── denúncia registrada ──► fila do ADMIN
                   │                              │
                   │      3+ denúncias abertas ──►│ status = EM_REVISAO (sai do feed)
                   │                              │
                   └──────────────────────────────┴──► ADMIN decide
                                                        ├─ IMPROCEDENTE → PUBLICADO
                                                        └─ PROCEDENTE   → REMOVIDO
                                                                          (soft delete +
                                                                           notificação ao autor
                                                                           + registro na auditoria)
```

A variável `MODERACAO_PREVIA=true` inverte o fluxo (todo post nasce `EM_REVISAO`) sem
alteração de código — deixe pronta, o hospital pode exigir isso depois da primeira polêmica.

**Aviso oficial nunca entra nesse fluxo.** Denúncia sobre aviso institucional vira
notificação ao ADMIN, não remoção automática.

### 8.4 Segurança e LGPD

- **Quatro papéis (RD002):** `COLABORADOR`, `RH`, `MARKETING`, `ADMIN` — verificados por
  `exige("permissao")`, nunca por `if` de papel espalhado nos endpoints.
- Senha com **Argon2id**. Nunca bcrypt, nunca SHA.
- Access token JWT de 15 min **no estado do React** (nunca `localStorage`) + refresh de 7 dias
  em cookie `httpOnly; Secure; SameSite=Strict`, com rotação a cada uso e blacklist no Redis.
- Rate limit: 5 tentativas de login/min por IP e por e-mail; bloqueio após 10 falhas.
- Aniversariantes: **dia e mês, nunca o ano**.
- EXIF removido de toda imagem enviada.
- Desligamento é `ativo = 0`, não exclusão — preserva a autoria histórica dos avisos.
- Headers no Caddy: CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy: same-origin`.
- `sentry_sdk` com `send_default_pii=False` e `before_send` removendo
  `senha`, `token`, `authorization`, `cpf`.

---

## 9. Estrutura de pastas

```
intranet-decos/
├── PROJETO.md                    ← este arquivo
├── CLAUDE.md                     ← "Leia PROJETO.md antes de qualquer alteração."
├── docker-compose.yml
├── docker-compose.prod.yml
├── Makefile
├── .env.example                  ← TODA variável documentada aqui
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py         # Pydantic Settings
│   │   │   ├── db.py             # engine, Base, mixins, sessão
│   │   │   ├── security.py       # Argon2, JWT, dependencies de papel
│   │   │   ├── storage.py        # cliente S3, upload, URL pré-assinada
│   │   │   ├── imagens.py        # EXIF, WebP, variantes
│   │   │   ├── logging.py        # structlog JSON
│   │   │   ├── observability.py  # sentry_sdk, middleware de request_id
│   │   │   └── auditoria.py      # listener SQLAlchemy que grava o diff
│   │   ├── modules/
│   │   │   ├── publicacoes/      # feed, avisos, posts, eventos
│   │   │   │   ├── models.py routers.py schemas.py services.py repositories.py
│   │   │   ├── interacoes/       # reações, comentários, denúncias, notificações
│   │   │   ├── documentos/       # POPs, versões, leituras, FAQ
│   │   │   ├── diretorio/        # setores, ramais, aniversariantes
│   │   │   └── identidade/       # usuários, login, papéis
│   │   ├── admin/                # sqladmin
│   │   ├── jobs/                 # APScheduler: expiração, aniversários, reconciliação
│   │   └── shared/               # exceções de domínio, paginação por cursor, normalizar()
│   ├── alembic/versions/
│   ├── tests/                    # espelha modules/
│   └── pyproject.toml            # ruff + mypy + pytest configurados aqui
│
├── frontend/
│   ├── src/
│   │   ├── app/                  # router, providers, layout, ErrorBoundary
│   │   ├── features/             # MESMOS NOMES dos módulos do backend
│   │   │   ├── publicacoes/ interacoes/ documentos/ diretorio/ identidade/
│   │   │   └── (cada um: api.ts, hooks.ts, components/, types.ts)
│   │   ├── components/ui/
│   │   └── lib/                  # apiClient (interceptor de refresh), sentry, formatadores
│   └── vite.config.ts
│
├── infra/
│   ├── Caddyfile
│   └── scripts/backup.sh
└── docs/
    ├── arquitetura.md
    ├── adr/                      # 1 arquivo por decisão que mudar depois
    └── modelo-dados.md
```

> **Convenção que economiza semanas:** `backend/app/modules/` e `frontend/src/features/`
> têm exatamente os mesmos nomes. Quem precisa mexer em "aniversariantes" sabe os dois
> lugares sem perguntar.

---

## 10. Contrato da API

Prefixo `/api/v1`. Toda listagem devolve `{ "itens": [...], "proximo_cursor": "..." }`.

```
POST   /auth/login                    e-mail + senha → access token + cookie de refresh
POST   /auth/refresh                  rotaciona o refresh
POST   /auth/logout                   invalida o refresh no Redis
GET    /auth/eu                       perfil do usuário logado

GET    /feed                          ?cursor=&tipo=&categoria=   (fixados vêm à parte)
POST   /publicacoes                   cria post/aviso/evento (tipo no corpo)
GET    /publicacoes/{id}
PATCH  /publicacoes/{id}
DELETE /publicacoes/{id}              arquiva (soft delete) — nunca apaga
POST   /publicacoes/{id}/anexos       multipart, múltiplas imagens
POST   /publicacoes/{id}/fixar        MARKETING+                      RF008
POST   /publicacoes/{id}/ciencia      "li e estou ciente"

PUT    /publicacoes/{id}/reacao       idempotente: cria ou troca o tipo
DELETE /publicacoes/{id}/reacao
GET    /publicacoes/{id}/comentarios
POST   /publicacoes/{id}/comentarios  ?id_comentario_pai= para resposta
DELETE /comentarios/{id}
POST   /denuncias

GET    /notificacoes                  ?nao_lidas=true
POST   /notificacoes/marcar-lidas

GET    /documentos                    ?busca=&categoria=&setor=
POST   /documentos                    ADMIN                           RF018
POST   /documentos/{id}/versoes       publica nova versão
GET    /documentos/{id}/download      302 para URL pré-assinada + registra leitura
GET    /documentos/{id}/leituras      quem leu qual versão (ADMIN)

GET    /faq                           ?busca=&categoria=

GET    /colaboradores                 ?busca=&setor=&andar=
GET    /colaboradores/{id}
GET    /setores
GET    /aniversariantes               ?mes=&setor=   (devolve dia e mês, sem ano)

GET    /eventos                       ?de=&ate=      (agenda)

GET    /moderacao/denuncias           ADMIN
POST   /moderacao/denuncias/{id}/resolver

GET    /health/live                   processo de pé
GET    /health/ready                  banco + bucket + redis respondendo
```

---

## 11. Convenções de código

**Idioma.** Domínio em português (`publicacoes`, `reacoes`, `excluido_em`); termos de framework
e infraestrutura em inglês (`router`, `service`, `repository`, `settings`). Não misture dentro
do mesmo identificador — nada de `criar_publicacao_handler_v2`.

**Três camadas, uma direção de dependência.**

| Camada | Pode importar | Nunca faz |
|---|---|---|
| Router | schemas, services, deps | escrever `select()`; conhecer nome de tabela |
| Service | repositories, models, storage | retornar `Response`; lançar `HTTPException` |
| Repository | models, session | decidir regra de negócio; dar `commit` |

Exceções de domínio (`RecursoNaoEncontrado`, `PermissaoNegada`, `RegraDeNegocioViolada`)
são traduzidas em HTTP num único `exception_handler` global — que também garante o
`request_id` no GlitchTip e no header `X-Request-ID` da resposta.

**Regras que reprovam o PR no code review:**

1. `Base.metadata.create_all()` em qualquer lugar, inclusive teste.
2. SQL cru com `LIMIT`/`OFFSET` — o Oracle usa `FETCH FIRST`.
3. Comparação ou gravação de string vazia — no Oracle `''` **é** `NULL`.
4. Comparação de tupla `(a, b) < (c, d)` — o Oracle não suporta.
5. `DELETE` físico em tabela de conteúdo.
6. URL de arquivo gravada no banco em vez de `bucket` + `object_key`.
7. Recurso exclusivo do Oracle 23ai (coluna `BOOLEAN`, tipo `JSON` nativo, `DROP IF EXISTS`)
   antes de o DBA confirmar a versão de produção.
8. `localStorage` guardando token.
9. Contador atualizado com leitura-e-escrita em vez de `+ 1` no `UPDATE`.
10. `print()` no lugar de `log.info()`.

**Commits:** Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`).
**Branches:** `feat/nome-curto`, `fix/nome-curto`. PR sem revisão de outro membro não entra.

---

## 12. Variáveis de ambiente

```bash
# ---------- Aplicação ----------
APP_NOME="Intranet Decós"
APP_AMBIENTE=dev                      # dev | homologacao | producao
APP_DEBUG=true
UVICORN_WORKERS=4                     # produção: 2 x vCPU, mínimo 4 (RNF004)
APP_URL=http://localhost:5173
SECRET_KEY=troque-isto-em-producao    # openssl rand -hex 32

# ---------- Banco ----------
# dev — container Oracle 23ai Free
DATABASE_URL=oracle+oracledb://INTRANET_APP:senha@oracle:1521/?service_name=FREEPDB1
# produção on-premise (preencher quando a credencial chegar)
# DATABASE_URL=oracle+oracledb://INTRANET_APP:senha@srv-oracle.decos.local:1521/?service_name=INTRAPDB
# Oracle Autonomous (OCI) — o python-oracledb thin lê o wallet sem Instant Client
# ORACLE_CONFIG_DIR=/opt/oracle/wallet
# ORACLE_WALLET_LOCATION=/opt/oracle/wallet
# ORACLE_WALLET_PASSWORD=
DB_POOL_SIZE=10                       # RNF004 — 160 usuários simultâneos
DB_MAX_OVERFLOW=10
DB_POOL_RECYCLE=1800                  # menor que o IDLE_TIME do profile Oracle

# ---------- Autenticação ----------
JWT_ACCESS_MINUTOS=15
JWT_REFRESH_DIAS=7
LOGIN_MAX_TENTATIVAS=5

# ---------- Storage ----------
S3_ENDPOINT=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_REGIAO=us-east-1
S3_BUCKET_MIDIA=decos-midia
S3_BUCKET_DOCUMENTOS=decos-documentos
S3_BUCKET_AVATARES=decos-avatares
S3_BUCKET_BACKUP=decos-backup
UPLOAD_MAX_MB_IMAGEM=10
UPLOAD_MAX_MB_ARQUIVO=25
URL_ASSINADA_MINUTOS=60

# ---------- Redis ----------
REDIS_URL=redis://redis:6379/0

# ---------- Observabilidade ----------
SENTRY_DSN=                           # DSN do GlitchTip
SENTRY_TRACES_SAMPLE_RATE=0.1
LOG_LEVEL=INFO
LOG_FORMATO=json

# ---------- Moderação ----------
MODERACAO_PREVIA=false
DENUNCIAS_PARA_REVISAO=3

# ---------- E-mail (SMTP interno) ----------
SMTP_HOST=
SMTP_PORT=587
SMTP_USUARIO=
SMTP_SENHA=
SMTP_REMETENTE=intranet@decos.local

# ---------- Frontend (prefixo VITE_) ----------
VITE_API_URL=http://localhost:8000/api/v1
VITE_SENTRY_DSN=
```

---

## 13. docker-compose

```yaml
services:
  oracle:
    image: gvenzl/oracle-free:23-slim
    environment:
      ORACLE_PASSWORD: ${ORACLE_ROOT_PASSWORD:-oracle}
      APP_USER: INTRANET_APP
      APP_USER_PASSWORD: senha
    ports: ["1521:1521"]
    volumes: ["oracle_data:/opt/oracle/oradata"]
    healthcheck:
      test: ["CMD", "healthcheck.sh"]
      interval: 10s
      timeout: 5s
      retries: 30

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${S3_ACCESS_KEY:-minioadmin}
      MINIO_ROOT_PASSWORD: ${S3_SECRET_KEY:-minioadmin}
    ports: ["9000:9000", "9001:9001"]
    volumes: ["minio_data:/data"]

  # Cria os buckets e LIGA O VERSIONAMENTO na criação.
  # Ligar depois não recupera o que já foi sobrescrito.
  minio-init:
    image: minio/mc:latest
    depends_on: [minio]
    entrypoint: >
      /bin/sh -c "
      mc alias set local http://minio:9000 $${S3_ACCESS_KEY} $${S3_SECRET_KEY};
      for b in decos-midia decos-documentos decos-avatares decos-backup; do
        mc mb --ignore-existing local/$$b;
        mc version enable local/$$b;
      done;
      "
    env_file: [.env]

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  glitchtip:
    image: glitchtip/glitchtip:latest
    depends_on: [glitchtip-db, redis]
    environment:
      DATABASE_URL: postgres://postgres:postgres@glitchtip-db:5432/glitchtip
      SECRET_KEY: ${SECRET_KEY}
      REDIS_URL: redis://redis:6379/1
    ports: ["8080:8080"]

  glitchtip-db:
    image: postgres:16-alpine
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: glitchtip
    volumes: ["glitchtip_data:/var/lib/postgresql/data"]

  backend:
    build: ./backend
    depends_on:
      oracle: {condition: service_healthy}
      minio: {condition: service_started}
      redis: {condition: service_started}
    env_file: [.env]
    ports: ["8000:8000"]
    volumes: ["./backend:/app"]
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    env_file: [.env]
    ports: ["5173:5173"]
    volumes: ["./frontend:/app", "/app/node_modules"]
    command: npm run dev -- --host

volumes:
  oracle_data:
  minio_data:
  glitchtip_data:
```

Em produção, `docker-compose.prod.yml` acrescenta o **Caddy** na frente, serve o build
estático do React, remove `--reload` e os volumes de código, e sobe o backend com
`uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS}` — os quatro
workers que o RNF004 exige (seção 6.6).

---

## 14. Setup em 10 minutos

```bash
git clone <repo> && cd intranet-decos
cp .env.example .env
make up          # sobe os containers, aplica as migrations, popula o seed
```

O `make up` executa:

```makefile
up:
	docker compose up -d
	docker compose exec backend alembic upgrade head
	docker compose exec backend python -m app.seed

migrate:
	docker compose exec backend alembic revision --autogenerate -m "$(m)"

test:
	docker compose exec backend pytest -v

sql:   # gera o script para o DBA do hospital executar
	docker compose exec backend alembic upgrade head --sql > migracao.sql
```

**Portas:** `:8000` FastAPI (`/docs` traz o Swagger) · `:5173` React · `:9001` console do MinIO ·
`:8080` GlitchTip · `:1521` Oracle · `:6379` Redis.

**Seed obrigatório desde a sprint 2:** 40 colaboradores em 8 setores e 3 andares, 20 avisos,
30 posts com fotos, 10 eventos, 15 POPs em 2 versões cada, 20 FAQs, reações e comentários
distribuídos. Nunca demonstre com tela vazia — e uma tela de feed vazia esconde bug de layout.

---

## 15. CI/CD

GitHub Actions em todo pull request, plano gratuito, alvo de 4 minutos:

| Etapa | Comando | Bloqueia merge |
|---|---|:--:|
| Lint | `ruff check` · `ruff format --check` · `eslint` · `prettier --check` | ✅ |
| Tipos | `mypy app` · `tsc --noEmit` | ✅ |
| Testes | `pytest --cov` (mínimo 60% nos *services*) contra Oracle em service container | ✅ |
| Migrations | banco vazio → `alembic upgrade head` → `alembic check` | ✅ |
| Build | imagem Docker + `vite build` com envio dos source maps ao GlitchTip | ✅ |
| Segurança | `pip-audit` · `npm audit` · `trivy image` | alerta |

Deploy: *self-hosted runner* se a TI liberar; senão
`git pull && docker compose -f docker-compose.prod.yml up -d --build` em janela combinada,
**com backup do banco tirado antes**.

---

## 16. Roadmap

| Sprint | Entrega |
|---|---|
| **1–2** | Fundação: Compose, Oracle 23ai, Alembic, três camadas, login Argon2 + JWT, GlitchTip e logs JSON ligados no primeiro commit. Entregável: erro proposital aparecendo no GlitchTip com `request_id`. |
| **3–4** | **Módulo Diretório** — setores com andar/bloco, colaboradores, ramais, busca, aniversariantes com coluna virtual, `sqladmin`, CI completa. É o módulo mais simples e serve para a equipe atravessar a stack inteira e fixar o padrão. Primeira demo. |
| **5–7** | **Publicações e feed** — a hierarquia `publicacoes`, avisos com prioridade e ciência, posts, eventos, feed com paginação por cursor, upload de fotos com EXIF removido e três variantes. |
| **8–9** | **Interações** — reações, comentários com um nível de resposta, notificações, denúncias e fila de moderação. |
| **10** | **Documentos e FAQ** — POPs com código, versionamento, registro de leitura, download por URL pré-assinada, FAQ com busca sem acento. |
| **11** | **Endurecimento** — auditoria completa, rate limit, **teste de carga do RNF004 com 160 VUs passando** (seção 6.6), teste de restauração de backup, acessibilidade WCAG AA, revisão de N+1 e índices. |
| **12** | **Entrega** — migração para o Oracle licenciado do hospital, homologação com colaboradores reais, manual do administrador, apresentação à banca. |

**Corte planejado se atrasar** (decidam agora, por escrito, não na sprint 10):
saem compartilhamento de post, inscrição em evento e contador de visualização do FAQ.
**Nunca saem:** autenticação, auditoria, backup, versionamento de documento, moderação
e a evidência do RNF004.

---

## 17. Definition of Done

Uma tarefa só está pronta quando:

- [ ] Migration Alembic criada e **revisada à mão** (nunca `create_all()`)
- [ ] Testes de service e repository passando, incluindo o caminho de erro
- [ ] `ruff`, `mypy` e `tsc` limpos
- [ ] Soft delete respeitado — nenhum `DELETE` físico
- [ ] Ação relevante gravada em `auditoria`
- [ ] Erro tratado por exceção de domínio, não `HTTPException` no service
- [ ] Endpoint documentado no OpenAPI com exemplo de resposta
- [ ] Seed atualizado se a tabela é nova
- [ ] Tela testada com dado longo (nome de 150 caracteres, aviso de 5.000 caracteres, 10 fotos)
- [ ] Nenhum `console.log` nem `print()` esquecido
- [ ] Permissão verificada por `exige("...")`, nunca por `if` de papel no endpoint
- [ ] Consulta nova conferida com `echo=True` — nenhum N+1 introduzido (RNF004)
- [ ] PR revisado por outro membro da equipe

---

## 18. Lacunas do escopo original, corrigidas

| Lacuna no documento do hospital | Correção neste blueprint |
|---|---|
| "Mural de eventos" é MVP mas **não tinha tabela** | `eventos` como subclasse de `publicacoes`, com `data_inicio NOT NULL`, `data_fim`, `local` |
| "Central de dúvidas (FAQ)" é MVP mas **não tinha tabela** | `faq` com categoria, ordenação manual e busca sem acento |
| Busca de ramal "por setor **e andar**", mas não havia campo de andar | `setores.andar` e `setores.bloco`, com índice |
| Ramal existia só por setor | `usuarios.ramal` (individual) + `setores.ramal_geral` |
| `DOCUMENTOS.URL_ARQUIVO VARCHAR2(500)` amarrava o banco ao host do storage | `bucket`, `object_key`, `version_id`, `mime_type`, `tamanho_bytes`, `checksum_sha256` |
| `CATEGORIA VARCHAR2(50)` como texto solto | Tabela `categorias` com FK, slug e tipo |
| Aviso sem ciclo de vida | `status`, `fixado`, `publicado_em`, `expira_em`, `visibilidade` |
| Usuário sem desligamento | `ativo`, `desligado_em`, `ultimo_login_em`, `role`, `bio`, `foto_object_key` |
| Sem trilha de auditoria | `auditoria` append-only com `diff` JSON e `request_id` |
| Sem soft delete — exclusão perdia informação | `excluido_em` em todo conteúdo + lixeira do ADMIN + purga só após 90 dias |
| POP sem histórico de versões | `documento_versoes` + `documento_leituras` (rastreabilidade de leitura) |
| Aniversariantes exigiam varrer a tabela | Colunas virtuais `nasc_mes` / `nasc_dia` com índice |
| Nada sobre a camada social | Hierarquia `publicacoes` + `reacoes`, `comentarios`, `anexos`, `denuncias`, `notificacoes` |
| Nada sobre moderação | Pós-moderação com fila, `EM_REVISAO` automático e `MODERACAO_PREVIA` configurável |
| Nada sobre privacidade de foto | EXIF removido no upload; avatar em bucket próprio com URL curta |

---

## 19. O que este projeto NÃO vai fazer

Escrito aqui para que ninguém proponha na sprint 7:

- **Kubernetes, microsserviços, service mesh.** São sete containers e ~300 usuários.
- **Elasticsearch / OpenSearch.** A coluna `*_busca` com índice resolve nesse volume.
- **Chat em tempo real / WebSocket.** Notificação é *polling* a cada 60 s no MVP.
- **Feed algorítmico.** Ordem cronológica decrescente, com fixados no topo. Ponto.
- **App mobile nativo.** O escopo diz "exclusivo desktop interno".
- **Celery / RabbitMQ.** APScheduler dá conta dos três jobs que existem.
- **GraphQL.** REST com OpenAPI é o que a banca e a equipe conseguem ler.
- **Integração com o prontuário ou qualquer sistema clínico.** A intranet não toca em dado de paciente,
  e essa fronteira não se negocia.

---

*Blueprint v1.0 · setembro de 2026 · baseado na especificação do Setor de Tecnologia do Hospital Decós.*
*Decisão que contrarie este arquivo precisa alterá-lo no mesmo pull request.*
