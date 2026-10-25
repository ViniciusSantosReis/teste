"""Schemas Pydantic de entrada e saída para autenticação e gestão de identidade."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Payload de entrada para o endpoint POST /auth/login."""

    email: EmailStr = Field(
        ...,
        description="E-mail corporativo cadastrado na instituição.",
        examples=["colaborador@decos.com.br"],
    )
    senha: str = Field(
        ...,
        min_length=1,
        description="Senha de acesso do colaborador.",
        examples=["SenhaSegura#123"],
    )


class SetorResumo(BaseModel):
    """Dados resumidos do setor para retorno em endpoints de usuário."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    sigla: str | None = None
    ramal_geral: str | None = None
    andar: str | None = None


class UsuarioOut(BaseModel):
    """Representação pública e segura do colaborador (perfil)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: EmailStr
    role: str
    cargo: str | None = None
    ramal: str | None = None
    foto_object_key: str | None = None
    id_setor: int | None = None
    setor: SetorResumo | None = None
    data_nascimento: date | None = None
    bio: str | None = None
    ultimo_login_em: datetime | None = None
    permissoes: list[str] = Field(
        default_factory=list,
        description="Lista de permissões granulares associadas ao papel do usuário.",
    )


class TokenResponse(BaseModel):
    """Resposta com Access Token retornado no login e no refresh de sessão."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        ...,
        description="Tempo de vida do token de acesso em segundos (ex: 900 para 15 minutos).",
    )
    usuario: UsuarioOut


class RefreshTokenRequest(BaseModel):
    """Fallback opcional de corpo para refresh em clientes que não utilizam cookies."""

    refresh_token: str | None = Field(
        default=None,
        description="Refresh token (caso não enviado via cookie httpOnly).",
    )


class MensagemResponse(BaseModel):
    """Resposta genérica para operações como logout."""

    mensagem: str
