"""Testes unitários do módulo de segurança: Argon2id e tokens JWT."""

import time
from datetime import datetime, timezone
import pytest

from app.core.security import (
    criar_access_token,
    criar_refresh_token,
    decodificar_token,
    gerar_senha_hash,
    verificar_senha,
)
from app.shared.exceptions import TokenInvalido


def test_argon2id_hashing_e_verificacao() -> None:
    """Valida que a senha é criptografada com Argon2id e verificada corretamente."""
    senha = "SenhaForte#HospitalDecos2026"
    hash_senha = gerar_senha_hash(senha)

    assert hash_senha != senha
    assert hash_senha.startswith("$argon2id$")
    assert verificar_senha(senha, hash_senha) is True
    assert verificar_senha("SenhaIncorreta", hash_senha) is False


def test_criar_e_decodificar_access_token() -> None:
    """Valida a emissão e leitura do access token JWT de 15 minutos."""
    payload_original = {
        "sub": "42",
        "email": "teste@decos.com.br",
        "role": "COLABORADOR",
    }
    token = criar_access_token(payload_original, expiracao_minutos=15)
    dados = decodificar_token(token, tipo_esperado="access")

    assert dados["sub"] == "42"
    assert dados["email"] == "teste@decos.com.br"
    assert dados["role"] == "COLABORADOR"
    assert dados["type"] == "access"
    assert "exp" in dados
    assert "iat" in dados


def test_criar_refresh_token_gera_jti_unico() -> None:
    """Valida que cada refresh token gerado possui um identificador (JTI) único."""
    token1, jti1, exp1 = criar_refresh_token(usuario_id=1)
    token2, jti2, exp2 = criar_refresh_token(usuario_id=1)

    assert token1 != token2
    assert jti1 != jti2
    assert exp1 > 0 and exp2 > 0

    dados = decodificar_token(token1, tipo_esperado="refresh")
    assert dados["sub"] == "1"
    assert dados["jti"] == jti1
    assert dados["type"] == "refresh"


def test_token_expirado_lanca_excecao() -> None:
    """Valida que tokens expirados disparam TokenInvalido."""
    # Gera token com expiração negativa (já expirado)
    token = criar_access_token({"sub": "1"}, expiracao_minutos=-1)

    with pytest.raises(TokenInvalido) as exc_info:
        decodificar_token(token)

    assert "expirado" in str(exc_info.value.mensagem).lower()


def test_token_invalido_ou_adulterado() -> None:
    """Valida que assinatura adulterada resulta em erro."""
    token = criar_access_token({"sub": "1"}, expiracao_minutos=15)
    token_adulterado = token[:-4] + "abcd"

    with pytest.raises(TokenInvalido) as exc_info:
        decodificar_token(token_adulterado)

    assert "inválido" in str(exc_info.value.mensagem).lower()
