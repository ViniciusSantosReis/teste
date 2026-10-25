"""Testes de regras de negócio da camada Service de Identidade."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.modules.identidade.models import Usuario
from app.modules.identidade.services import IdentidadeService
from app.shared.exceptions import (
    CredenciaisInvalidas,
    TentativasExcedidas,
    TokenRevogado,
    UsuarioInativo,
)


def test_autenticar_sucesso(
    usuario_colaborador: Usuario,
    senha_padrao_teste: str,
    mock_redis: dict[str, str],
) -> None:
    """Valida o fluxo completo de login bem-sucedido."""
    session = MagicMock()
    service = IdentidadeService(session)

    # Mock do repository
    service.repository.obter_por_email = MagicMock(return_value=usuario_colaborador)
    service.repository.atualizar_ultimo_login = MagicMock()
    service.repository.registrar_auditoria = MagicMock()

    resposta, refresh_token, exp = service.autenticar(
        email=usuario_colaborador.email,
        senha=senha_padrao_teste,
        ip_origem="192.168.1.10",
        request_id="req-123",
    )

    assert resposta.access_token is not None
    assert resposta.token_type == "bearer"
    assert resposta.usuario.email == usuario_colaborador.email
    assert "conteudo:criar" in resposta.usuario.permissoes
    assert refresh_token is not None
    assert exp > 0

    # Valida atualização do último login e auditoria
    service.repository.atualizar_ultimo_login.assert_called_once()
    service.repository.registrar_auditoria.assert_called_once_with(
        entidade="usuarios",
        entidade_id=usuario_colaborador.id,
        acao="LOGIN",
        id_usuario=usuario_colaborador.id,
        request_id="req-123",
        ip_origem="192.168.1.10",
    )
    session.commit.assert_called_once()


def test_autenticar_senha_incorreta(
    usuario_colaborador: Usuario,
    mock_redis: dict[str, str],
) -> None:
    """Valida que senha inválida dispara CredenciaisInvalidas e registra auditoria."""
    session = MagicMock()
    service = IdentidadeService(session)

    service.repository.obter_por_email = MagicMock(return_value=usuario_colaborador)
    service.repository.registrar_auditoria = MagicMock()

    with pytest.raises(CredenciaisInvalidas):
        service.autenticar(
            email=usuario_colaborador.email,
            senha="SenhaErradaNaoConfere",
            ip_origem="192.168.1.10",
            request_id="req-falha-1",
        )

    service.repository.registrar_auditoria.assert_called_once()
    args, kwargs = service.repository.registrar_auditoria.call_args
    assert kwargs["acao"] == "LOGIN_FALHA"
    session.commit.assert_called_once()


def test_autenticar_usuario_nao_encontrado(
    mock_redis: dict[str, str],
) -> None:
    """Valida que e-mail inexistente dispara CredenciaisInvalidas."""
    session = MagicMock()
    service = IdentidadeService(session)

    service.repository.obter_por_email = MagicMock(return_value=None)
    service.repository.registrar_auditoria = MagicMock()

    with pytest.raises(CredenciaisInvalidas):
        service.autenticar(
            email="nao.existe@decos.com.br",
            senha="QualquerSenha123",
        )

    service.repository.registrar_auditoria.assert_called_once()


def test_autenticar_usuario_inativo_ou_desligado(
    usuario_colaborador: Usuario,
    senha_padrao_teste: str,
    mock_redis: dict[str, str],
) -> None:
    """Valida que colaboradores inativos têm o acesso recusado com UsuarioInativo."""
    session = MagicMock()
    service = IdentidadeService(session)

    # Simula colaborador desativado
    usuario_colaborador.ativo = False
    service.repository.obter_por_email = MagicMock(return_value=usuario_colaborador)

    with pytest.raises(UsuarioInativo):
        service.autenticar(
            email=usuario_colaborador.email,
            senha=senha_padrao_teste,
        )


def test_renovar_sessao_e_rotacao_de_token(
    usuario_colaborador: Usuario,
    senha_padrao_teste: str,
    mock_redis: dict[str, str],
) -> None:
    """Valida a rotação de refresh token: emite novo par e invalida o anterior."""
    session = MagicMock()
    service = IdentidadeService(session)

    service.repository.obter_por_email = MagicMock(return_value=usuario_colaborador)
    service.repository.obter_por_id = MagicMock(return_value=usuario_colaborador)

    # 1. Realiza login inicial
    _, refresh_token_inicial, _ = service.autenticar(
        email=usuario_colaborador.email,
        senha=senha_padrao_teste,
    )

    # 2. Renova a sessão usando o token
    resposta_renovada, novo_refresh_token, _ = service.renovar_sessao(
        refresh_token_inicial
    )

    assert resposta_renovada.access_token is not None
    assert novo_refresh_token != refresh_token_inicial

    # 3. Tenta reutilizar o token antigo -> deve ser recusado por estar na blacklist
    with pytest.raises(TokenRevogado):
        service.renovar_sessao(refresh_token_inicial)
