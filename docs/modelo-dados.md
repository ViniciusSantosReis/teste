# Modelo de dados

> Preencher na sprint 1. Referência: seções 3 a 6 do PROJETO.md (DDL, modelos SQLAlchemy,
> consultas críticas e índices).

## Diagrama
<!-- ER das entidades: usuarios, setores, publicacoes e sua hierarquia, anexos, reacoes,
     comentarios, denuncias, notificacoes, documentos, versoes, leituras, faq, auditoria. -->

## Decisões que valem repetir
<!-- Soft delete em todo conteúdo. Aniversário sem o ano. Contador incrementado no UPDATE.
     bucket + object_key, nunca URL. -->

## Índices
<!-- Um por consulta crítica, com o motivo ao lado. -->

## Papéis
<!-- usuarios.role com CHECK (role IN ('COLABORADOR','RH','MARKETING','ADMIN')) — RD002.
     RH gerencia setor, ramal e usuário; MARKETING gerencia aviso, evento, fixação e categoria. -->
