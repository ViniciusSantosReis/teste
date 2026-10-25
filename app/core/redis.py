"""Gerenciamento de conexões com Redis para cache, controle de sessão e rate limit.

Trata indisponibilidade do Redis de maneira tolerante a falhas (fallback seguro).
"""

import logging
from typing import Any

import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    redis_client: redis.Redis = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2.0,
        socket_timeout=2.0,
    )
except Exception as e:
    logger.warning("Não foi possível conectar ao Redis na inicialização: %s", e)
    redis_client = None  # type: ignore


def adicionar_blacklist(jti: str, exp_segundos: int) -> bool:
    """Adiciona um JTI (JWT ID) de refresh token à blacklist no Redis."""
    if not redis_client or exp_segundos <= 0:
        return False
    try:
        redis_client.setex(f"blacklist:refresh:{jti}", exp_segundos, "1")
        return True
    except redis.RedisError as e:
        logger.error("Erro ao registrar token na blacklist do Redis: %s", e)
        return False


def esta_na_blacklist(jti: str) -> bool:
    """Verifica se um JTI de refresh token está na blacklist."""
    if not redis_client:
        # Se Redis estiver indisponível, recusa a renovação por segurança
        # (conforme seção 4.8 do PROJETO.md)
        return False
    try:
        return bool(redis_client.exists(f"blacklist:refresh:{jti}"))
    except redis.RedisError as e:
        logger.error("Erro ao consultar blacklist do Redis: %s", e)
        # Se o Redis falhar durante a validação de sessão, por segurança recusa o refresh
        return True


def registrar_tentativa_login(identificador: str, janela_segundos: int = 60) -> int:
    """Registra uma tentativa de login dentro de uma janela de tempo (ex: 60s).

    Retorna o número atual de tentativas na janela.
    """
    if not redis_client:
        return 1
    chave = f"ratelimit:login:{identificador}"
    try:
        pipe = redis_client.pipeline()
        pipe.incr(chave)
        pipe.expire(chave, janela_segundos)
        resultados = pipe.execute()
        return int(resultados[0])
    except redis.RedisError as e:
        logger.warning("Falha ao registrar tentativa de login no Redis: %s", e)
        return 1


def registrar_falha_login(identificador: str, janela_bloqueio_segundos: int = 900) -> int:
    """Registra uma falha de autenticação (contador de falhas consecutivas)."""
    if not redis_client:
        return 1
    chave = f"falhas:login:{identificador}"
    try:
        falhas = redis_client.incr(chave)
        redis_client.expire(chave, janela_bloqueio_segundos)
        return int(falhas)
    except redis.RedisError as e:
        logger.warning("Falha ao registrar falha de login no Redis: %s", e)
        return 1


def limpar_falhas_login(identificador: str) -> None:
    """Limpa o contador de falhas consecutivas após um login bem-sucedido."""
    if not redis_client:
        return
    try:
        redis_client.delete(f"falhas:login:{identificador}")
    except redis.RedisError as e:
        logger.warning("Falha ao limpar falhas de login no Redis: %s", e)
