"""Camada Router: Endpoints de autenticação e sessão da Intranet Decós.

Rotas expostas sob /api/v1/auth:
- POST /login: Validação de e-mail e senha, emissão de Access Token e cookie de Refresh.
- POST /refresh: Rotação transparente de Refresh Token.
- POST /logout: Revogação da sessão no Redis e remoção do cookie.
- GET  /eu: Perfil e permissões granulares do colaborador autenticado.
"""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import obter_usuario_atual
from app.modules.identidade.models import Usuario
from app.modules.identidade.schemas import (
    LoginRequest,
    MensagemResponse,
    RefreshTokenRequest,
    TokenResponse,
    UsuarioOut,
)
from app.modules.identidade.services import IdentidadeService
from app.shared.exceptions import TokenInvalido

router = APIRouter()
settings = get_settings()


def get_identidade_service(db: Session = Depends(get_db)) -> IdentidadeService:
    """Dependency que instancia a camada Service com a sessão do banco."""
    return IdentidadeService(db)


def extrair_ip_cliente(request: Request) -> str:
    """Extrai o IP real do cliente, respeitando proxies reversos (ex: Caddy/Nginx)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login de colaborador",
    description="Autentica o colaborador via e-mail e senha (Argon2id). Retorna o Access Token "
    "e define o cookie httpOnly com o Refresh Token.",
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: IdentidadeService = Depends(get_identidade_service),
) -> TokenResponse:
    """Realiza autenticação com e-mail corporativo e senha."""
    ip_origem = extrair_ip_cliente(request)
    request_id = getattr(request.state, "request_id", None)

    resposta_token, refresh_token, exp_segundos = service.autenticar(
        email=payload.email,
        senha=payload.senha,
        ip_origem=ip_origem,
        request_id=request_id,
    )

    # Gravação do cookie httpOnly estritamente seguro para mitigação de XSS
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=exp_segundos,
        httponly=True,
        secure=(settings.APP_AMBIENTE == "producao"),
        samesite="lax",
        path="/api/v1/auth",
    )

    return resposta_token


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Renovar token de acesso",
    description="Lê o Refresh Token do cookie httpOnly, valida na blacklist do Redis, "
    "rotaciona o token e emite um novo Access Token.",
)
def renovar_token(
    request: Request,
    response: Response,
    body: RefreshTokenRequest | None = None,
    service: IdentidadeService = Depends(get_identidade_service),
) -> TokenResponse:
    """Rotaciona o refresh token e emite novo access token."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token and body and body.refresh_token:
        refresh_token = body.refresh_token

    if not refresh_token:
        raise TokenInvalido("Cookie de sessão 'refresh_token' não encontrado.")

    resposta_token, novo_refresh_token, exp_segundos = service.renovar_sessao(
        refresh_token
    )

    response.set_cookie(
        key="refresh_token",
        value=novo_refresh_token,
        max_age=exp_segundos,
        httponly=True,
        secure=(settings.APP_AMBIENTE == "producao"),
        samesite="lax",
        path="/api/v1/auth",
    )

    return resposta_token


@router.post(
    "/logout",
    response_model=MensagemResponse,
    status_code=status.HTTP_200_OK,
    summary="Encerrar sessão (Logout)",
    description="Invalida o Refresh Token atual adicionando-o à blacklist do Redis e remove o cookie.",
)
def logout(
    request: Request,
    response: Response,
    body: RefreshTokenRequest | None = None,
    service: IdentidadeService = Depends(get_identidade_service),
) -> MensagemResponse:
    """Encerra a sessão do colaborador e revoga o refresh token."""
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token and body and body.refresh_token:
        refresh_token = body.refresh_token

    service.encerrar_sessao(refresh_token)

    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
    )

    return MensagemResponse(mensagem="Logout realizado com sucesso.")


@router.get(
    "/eu",
    response_model=UsuarioOut,
    status_code=status.HTTP_200_OK,
    summary="Perfil do colaborador autenticado",
    description="Retorna dados cadastrais, setor e permissões concedidas ao usuário ativo.",
)
def obter_usuario_logado(
    usuario: Usuario = Depends(obter_usuario_atual),
    service: IdentidadeService = Depends(get_identidade_service),
) -> UsuarioOut:
    """Retorna o perfil do colaborador autenticado com suas permissões."""
    return service.obter_perfil(usuario)
