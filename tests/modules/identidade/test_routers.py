"""Testes de integração dos endpoints HTTP de autenticação (/api/v1/auth)."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.core.security import criar_access_token
from app.main import app
from app.modules.identidade.models import Usuario
from app.modules.identidade.routers import get_identidade_service
from app.modules.identidade.schemas import SetorResumo, TokenResponse, UsuarioOut
from app.shared.exceptions import CredenciaisInvalidas


def test_endpoint_login_sucesso(
    client: TestClient,
    usuario_colaborador: Usuario,
    mock_redis: dict[str, str],
) -> None:
    """Valida POST /api/v1/auth/login retornando 200 e gravando cookie httpOnly."""
    service_mock = MagicMock()
    token_resp = TokenResponse(
        access_token="fake.jwt.token",
        token_type="bearer",
        expires_in=900,
        usuario=UsuarioOut(
            id=usuario_colaborador.id,
            nome=usuario_colaborador.nome,
            email=usuario_colaborador.email,
            role=usuario_colaborador.role,
            permissoes=["conteudo:criar"],
        ),
    )
    service_mock.autenticar.return_value = (token_resp, "fake_refresh_token_xyz", 604800)

    app.dependency_overrides[get_identidade_service] = lambda: service_mock

    try:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "ana.silva@decos.com.br",
                "senha": "SenhaCorreta#123",
            },
        )

        assert response.status_code == 200
        dados = response.json()
        assert dados["access_token"] == "fake.jwt.token"
        assert dados["usuario"]["email"] == "ana.silva@decos.com.br"
        assert "refresh_token" in response.cookies
        assert response.cookies["refresh_token"] == "fake_refresh_token_xyz"
    finally:
        app.dependency_overrides.pop(get_identidade_service, None)


def test_endpoint_login_credenciais_invalidas(
    client: TestClient,
    mock_redis: dict[str, str],
) -> None:
    """Valida POST /api/v1/auth/login retornando 401 para credenciais incorretas."""
    service_mock = MagicMock()
    service_mock.autenticar.side_effect = CredenciaisInvalidas("E-mail ou senha incorretos.")

    app.dependency_overrides[get_identidade_service] = lambda: service_mock

    try:
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "ana.silva@decos.com.br",
                "senha": "SenhaErrada",
            },
        )

        assert response.status_code == 401
        dados = response.json()
        assert dados["codigo"] == "CREDENCIAIS_INVALIDAS"
        assert "E-mail ou senha incorretos" in dados["detail"]
    finally:
        app.dependency_overrides.pop(get_identidade_service, None)


def test_endpoint_login_validacao_payload_invalido(client: TestClient) -> None:
    """Valida erro 422 quando o e-mail é malformado."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "email_invalido_sem_arroba",
            "senha": "123",
        },
    )
    assert response.status_code == 422
    assert response.json()["codigo"] == "VALIDACAO_ERRO"


def test_endpoint_logout(client: TestClient) -> None:
    """Valida POST /api/v1/auth/logout invalidando o cookie de sessão."""
    service_mock = MagicMock()
    app.dependency_overrides[get_identidade_service] = lambda: service_mock

    try:
        response = client.post(
            "/api/v1/auth/logout",
            cookies={"refresh_token": "token_a_ser_apagado"},
        )
        assert response.status_code == 200
        assert "Logout realizado com sucesso" in response.json()["mensagem"]
        service_mock.encerrar_sessao.assert_called_once_with("token_a_ser_apagado")
    finally:
        app.dependency_overrides.pop(get_identidade_service, None)


def test_endpoint_eu_sem_token(client: TestClient) -> None:
    """Valida que GET /api/v1/auth/eu rejeita requisições não autenticadas com 401."""
    response = client.get("/api/v1/auth/eu")
    assert response.status_code == 401
    assert response.json()["codigo"] == "TOKEN_INVALIDO"
