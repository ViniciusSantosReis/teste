"""Configuração de logs estruturados em JSON utilizando structlog.

Garante que dados sensíveis (senhas, tokens, CPF, segredos) nunca sejam
registrados em logs ou traces.
"""

import logging
import sys
from typing import Any

import structlog

from app.core.config import get_settings

CHAVES_SENSIVEIS = {
    "senha",
    "password",
    "senha_hash",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "secret",
    "secret_key",
    "cpf",
}


def sanitizar_dados_sensiveis(
    _logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Remove ou mascara campos sensíveis do dicionário de evento de log."""
    for chave in list(event_dict.keys()):
        if chave.lower() in CHAVES_SENSIVEIS:
            event_dict[chave] = "[REDACTED]"
    return event_dict


def configurar_logging() -> None:
    """Inicializa a infraestrutura de logging estruturado."""
    settings = get_settings()

    nivel = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=nivel,
    )

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        sanitizar_dados_sensiveis,
    ]

    if settings.LOG_FORMATO == "json":
        shared_processors.append(structlog.processors.JSONRenderer())
    else:
        shared_processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=shared_processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
