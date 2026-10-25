"""Segurança: Hashing com Argon2id, emissão e validação de tokens JWT."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
import jwt
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.modules.identidade.models import Usuario
from app.shared.exceptions import (
    CredenciaisInvalidas,
    TokenInvalido,
    UsuarioInativo,
)

settings = get_settings()
_hasher = PasswordHasher()


def gerar_senha_hash(senha: str) -> str:
    """Gera o hash da senha utilizando exclusivamente Argon2id."""
    return _hasher.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Verifica se a senha em texto confere com o hash Argon2id."""
    try:
        return _hasher.verify(senha_hash, senha)
    except (VerifyMismatchError, InvalidHashError):
        # Fallback de compatibilidade se houver prefixos passlib
        try:
            from passlib.context import CryptContext
            ctx = CryptContext(schemes=["argon2"], deprecated="auto")
            return bool(ctx.verify(senha, senha_hash))
        except Exception:
            return False


def criar_access_token(
    dados: dict[str, Any],
    expiracao_minutos: int | None = None,
) -> str:
    """Gera um JWT de curta duração (15 minutos) mantido em memória pelo frontend."""
    minutos = expiracao_minutos or settings.JWT_ACCESS_MINUTOS
    agora = datetime.now(timezone.utc)
    exp = agora + timedelta(minutes=minutos)

    payload = dados.copy()
    payload.update({
        "exp": exp,
        "iat": agora,
        "type": "access",
    })
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITMO)


def criar_refresh_token(usuario_id: int) -> tuple[str, str, int]:
    """Gera um Refresh Token JWT (7 dias) com JTI único para suporte a blacklist e rotação.

    Retorna:
        tuple[token, jti, segundos_restantes]
    """
    dias = settings.JWT_REFRESH_DIAS
    agora = datetime.now(timezone.utc)
    exp_delta = timedelta(days=dias)
    exp = agora + exp_delta
    jti = str(uuid.uuid4())

    payload = {
        "sub": str(usuario_id),
        "jti": jti,
        "type": "refresh",
        "exp": exp,
        "iat": agora,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITMO)
    return token, jti, int(exp_delta.total_seconds())


def decodificar_token(token: str, tipo_esperado: str | None = None) -> dict[str, Any]:
    """Decodifica e valida assinatura e expiração de um token JWT."""
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITMO],
        )
    except jwt.ExpiredSignatureError as e:
        raise TokenInvalido("Token expirado. Por favor, realize novo login.") from e
    except jwt.InvalidTokenError as e:
        raise TokenInvalido("Token inválido ou adulterado.") from e

    if tipo_esperado and payload.get("type") != tipo_esperado:
        raise TokenInvalido(f"Tipo de token inválido. Esperado: {tipo_esperado}.")

    return payload


def obter_usuario_atual(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Usuario:
    """Dependência FastAPI que extrai e valida o token Bearer do cabeçalho Authorization."""
    if not authorization or not authorization.startswith("Bearer "):
        raise TokenInvalido("Cabeçalho de autorização ausente ou em formato inválido.")

    token = authorization.removeprefix("Bearer ").strip()
    payload = decodificar_token(token, tipo_esperado="access")

    sub = payload.get("sub")
    if not sub:
        raise TokenInvalido("Token sem identificador de usuário (sub).")

    try:
        usuario_id = int(sub)
    except ValueError as e:
        raise TokenInvalido("Identificador de usuário inválido no token.") from e

    usuario = db.get(Usuario, usuario_id)
    if not usuario:
        raise CredenciaisInvalidas("Usuário associado ao token não existe.")

    if not usuario.ativo or usuario.desligado_em is not None:
        raise UsuarioInativo("Acesso bloqueado: usuário inativo ou desligado.")

    return usuario
