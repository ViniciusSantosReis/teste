"""Script de carga inicial (seed) com os perfis e personas especificados no projeto.

Cria os setores hospitalares e cadastra os quatro usuários do briefing:
- Ana Silva (Enfermeira / COLABORADOR)
- Roberto Almeida (Analista de Sistemas / ADMIN)
- Camila Costa (Marketing / MARKETING)
- Daniel Oliveira (Gestor de RH / RH)

Senha padrão para desenvolvimento de todos os usuários: Decos@2026
"""

from datetime import date

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.security import gerar_senha_hash
from app.modules.diretorio.models import Setor
from app.modules.identidade.models import Usuario
from app.shared.texto import normalizar


def executar_seed() -> None:
    """Executa o povoamento inicial do banco de dados."""
    senha_padrao = "Decos@2026"
    senha_hash = gerar_senha_hash(senha_padrao)

    with SessionLocal() as session:
        # 1. Cadastro de Setores
        setores_dados = [
            {
                "nome": "Tecnologia da Informação",
                "sigla": "TI",
                "ramal_geral": "1001",
                "andar": "3º Andar",
                "bloco": "Bloco A",
            },
            {
                "nome": "Recursos Humanos",
                "sigla": "RH",
                "ramal_geral": "1002",
                "andar": "2º Andar",
                "bloco": "Bloco A",
            },
            {
                "nome": "Marketing e Comunicação",
                "sigla": "MKT",
                "ramal_geral": "1003",
                "andar": "2º Andar",
                "bloco": "Bloco B",
            },
            {
                "nome": "Enfermagem e Assistência",
                "sigla": "ENF",
                "ramal_geral": "2001",
                "andar": "1º Andar",
                "bloco": "Bloco Central",
            },
            {
                "nome": "Diretoria Geral",
                "sigla": "DIR",
                "ramal_geral": "3001",
                "andar": "4º Andar",
                "bloco": "Bloco A",
            },
        ]

        setores_map: dict[str, Setor] = {}
        for s in setores_dados:
            stmt = select(Setor).where(Setor.nome == s["nome"])
            existente = session.scalars(stmt).first()
            if not existente:
                novo_setor = Setor(
                    nome=s["nome"],
                    nome_busca=normalizar(s["nome"]),
                    sigla=s["sigla"],
                    ramal_geral=s["ramal_geral"],
                    andar=s["andar"],
                    bloco=s["bloco"],
                    ativo=True,
                )
                session.add(novo_setor)
                session.flush()
                setores_map[s["sigla"]] = novo_setor
            else:
                setores_map[s["sigla"]] = existente

        # 2. Cadastro de Usuários (Personas)
        usuarios_dados = [
            {
                "nome": "Ana Silva",
                "email": "ana.silva@decos.com.br",
                "cargo": "Enfermeira",
                "role": "COLABORADOR",
                "ramal": "2015",
                "setor_sigla": "ENF",
                "data_nascimento": date(1988, 5, 14),
                "data_admissao": date(2021, 3, 1),
                "bio": "Profissional dedicada ao cuidado dos pacientes. Foco em protocolos de assistência rápida.",
            },
            {
                "nome": "Roberto Almeida",
                "email": "roberto.almeida@decos.com.br",
                "cargo": "Analista de Sistemas",
                "role": "ADMIN",
                "ramal": "1010",
                "setor_sigla": "TI",
                "data_nascimento": date(1996, 8, 22),
                "data_admissao": date(2020, 1, 15),
                "bio": "Gerenciamento de infraestrutura, servidores e sustentação da intranet hospitalar.",
            },
            {
                "nome": "Camila Costa",
                "email": "camila.costa@decos.com.br",
                "cargo": "Analista de Marketing",
                "role": "MARKETING",
                "ramal": "1025",
                "setor_sigla": "MKT",
                "data_nascimento": date(1997, 11, 3),
                "data_admissao": date(2022, 6, 10),
                "bio": "Comunicação interna, engajamento e divulgação institucional.",
            },
            {
                "nome": "Daniel Oliveira",
                "email": "daniel.oliveira@decos.com.br",
                "cargo": "Gestor de Recursos Humanos",
                "role": "RH",
                "ramal": "1030",
                "setor_sigla": "RH",
                "data_nascimento": date(1981, 2, 19),
                "data_admissao": date(2018, 9, 20),
                "bio": "Gestão de talentos, integração e políticas corporativas.",
            },
        ]

        for u in usuarios_dados:
            stmt_user = select(Usuario).where(Usuario.email == u["email"])
            usuario_existente = session.scalars(stmt_user).first()
            if not usuario_existente:
                setor_obj = setores_map.get(u["setor_sigla"])
                novo_usuario = Usuario(
                    nome=u["nome"],
                    nome_busca=normalizar(u["nome"]),
                    email=u["email"],
                    senha_hash=senha_hash,
                    cargo=u["cargo"],
                    role=u["role"],
                    ramal=u["ramal"],
                    id_setor=setor_obj.id if setor_obj else None,
                    data_nascimento=u["data_nascimento"],
                    data_admissao=u["data_admissao"],
                    bio=u["bio"],
                    ativo=True,
                )
                session.add(novo_usuario)

        session.commit()


if __name__ == "__main__":
    executar_seed()
