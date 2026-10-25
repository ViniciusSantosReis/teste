"""Fixtures compartilhadas para testes automatizados com pytest."""

from collections.abc import Generator
from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, get_db
from app.core.security import gerar_senha_hash
from app.main import app
from app.modules.diretorio.models import Setor
from app.modules.identidade.models import Usuario
from app.shared.texto import normalizar


@pytest.fixture(scope="session")
def senha_padrao_teste() -> str:
    """Senha padrão conhecida para testes de autenticação."""
    return "SenhaTeste#2026"


@pytest.fixture(scope="session")
def senha_hash_teste(senha_padrao_teste: str) -> str:
    """Hash Argon2id pré-computado para acelerar a execução da suíte de testes."""
    return gerar_senha_hash(senha_padrao_teste)


@pytest.fixture
def mock_redis(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Mock em memória do Redis para testes unitários de blacklist e rate limit."""
    armazenamento: dict[str, str] = {}
    falhas_storage: dict[str, int] = {}
    tentativas_storage: dict[str, int] = {}

    def fake_adicionar_blacklist(jti: str, _exp_segundos: int) -> bool:
        armazenamento[f"blacklist:refresh:{jti}"] = "1"
        return True

    def fake_esta_na_blacklist(jti: str) -> bool:
        return f"blacklist:refresh:{jti}" in armazenamento

    def fake_registrar_tentativa(chave: str, _janela: int = 60) -> int:
        atual = tentativas_storage.get(chave, 0) + 1
        tentativas_storage[chave] = atual
        return atual

    def fake_registrar_falha(chave: str, _janela: int = 900) -> int:
        atual = falhas_storage.get(chave, 0) + 1
        falhas_storage[chave] = atual
        return atual

    def fake_limpar_falhas(chave: str) -> None:
        falhas_storage.pop(chave, None)

    monkeypatch.setattr("app.core.redis.adicionar_blacklist", fake_adicionar_blacklist)
    monkeypatch.setattr("app.core.redis.esta_na_blacklist", fake_esta_na_blacklist)
    monkeypatch.setattr(
        "app.core.redis.registrar_tentativa_login", fake_registrar_tentativa
    )
    monkeypatch.setattr("app.core.redis.registrar_falha_login", fake_registrar_falha)
    monkeypatch.setattr("app.core.redis.limpar_falhas_login", fake_limpar_falhas)

    monkeypatch.setattr(
        "app.modules.identidade.services.adicionar_blacklist", fake_adicionar_blacklist
    )
    monkeypatch.setattr(
        "app.modules.identidade.services.esta_na_blacklist", fake_esta_na_blacklist
    )
    monkeypatch.setattr(
        "app.modules.identidade.services.registrar_tentativa_login",
        fake_registrar_tentativa,
    )
    monkeypatch.setattr(
        "app.modules.identidade.services.registrar_falha_login", fake_registrar_falha
    )
    monkeypatch.setattr(
        "app.modules.identidade.services.limpar_falhas_login", fake_limpar_falhas
    )

    return armazenamento


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Sessão com transação isolada para os testes."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Cliente de teste HTTP do FastAPI com sessão injetada."""

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def usuario_colaborador(senha_hash_teste: str) -> Usuario:
    """Instância simulada de colaborador comum (enfermeira)."""
    usuario = Usuario(
        id=101,
        nome="Ana Silva",
        nome_busca=normalizar("Ana Silva"),
        email="ana.silva@decos.com.br",
        senha_hash=senha_hash_teste,
        cargo="Enfermeira",
        role="COLABORADOR",
        ramal="2015",
        data_nascimento=date(1988, 5, 14),
        ativo=True,
    )
    usuario.setor = Setor(
        id=1,
        nome="Enfermagem",
        nome_busca="enfermagem",
        sigla="ENF",
        ramal_geral="2001",
        andar="1º Andar",
        ativo=True,
    )
    return usuario


@pytest.fixture
def usuario_admin(senha_hash_teste: str) -> Usuario:
    """Instância simulada de administrador do sistema (TI)."""
    usuario = Usuario(
        id=102,
        nome="Roberto Almeida",
        nome_busca=normalizar("Roberto Almeida"),
        email="roberto.almeida@decos.com.br",
        senha_hash=senha_hash_teste,
        cargo="Analista de Sistemas",
        role="ADMIN",
        ramal="1010",
        data_nascimento=date(1996, 8, 22),
        ativo=True,
    )
    usuario.setor = Setor(
        id=2,
        nome="Tecnologia da Informação",
        nome_busca="tecnologia da informacao",
        sigla="TI",
        ramal_geral="1001",
        andar="3º Andar",
        ativo=True,
    )
    return usuario


@pytest.fixture
def usuario_rh(senha_hash_teste: str) -> Usuario:
    """Instância simulada de gestor de Recursos Humanos."""
    usuario = Usuario(
        id=103,
        nome="Daniel Oliveira",
        nome_busca=normalizar("Daniel Oliveira"),
        email="daniel.oliveira@decos.com.br",
        senha_hash=senha_hash_teste,
        cargo="Gestor de Recursos Humanos",
        role="RH",
        ramal="1030",
        data_nascimento=date(1981, 2, 19),
        ativo=True,
    )
    usuario.setor = Setor(
        id=3,
        nome="Recursos Humanos",
        nome_busca="recursos humanos",
        sigla="RH",
        ramal_geral="1002",
        andar="2º Andar",
        ativo=True,
    )
    return usuario


@pytest.fixture
def usuario_marketing(senha_hash_teste: str) -> Usuario:
    """Instância simulada de analista de Marketing."""
    usuario = Usuario(
        id=104,
        nome="Camila Costa",
        nome_busca=normalizar("Camila Costa"),
        email="camila.costa@decos.com.br",
        senha_hash=senha_hash_teste,
        cargo="Analista de Marketing",
        role="MARKETING",
        ramal="1025",
        data_nascimento=date(1997, 11, 3),
        ativo=True,
    )
    usuario.setor = Setor(
        id=4,
        nome="Marketing e Comunicação",
        nome_busca="marketing e comunicacao",
        sigla="MKT",
        ramal_geral="1003",
        andar="2º Andar",
        ativo=True,
    )
    return usuario
