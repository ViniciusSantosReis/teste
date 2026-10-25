"""Observabilidade: middleware de request_id, rastreamento de erros e integração com GlitchTip/Sentry."""

import uuid
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog

from app.core.config import get_settings

settings = get_settings()
logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Gera ou propaga o identificador único X-Request-ID para cada requisição HTTP."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Any],
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Associa ao contexto de logging estruturado
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def configurar_observabilidade() -> None:
    """Configura o sentry-sdk (GlitchTip) caso o DSN esteja preenchido."""
    if not settings.SENTRY_DSN:
        return

    try:
        import sentry_sdk

        def filtrar_pii(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
            # Sanitiza headers de autenticação
            request_data = event.get("request", {})
            headers = request_data.get("headers", {})
            for cabecalho in ("authorization", "cookie"):
                if cabecalho in headers:
                    headers[cabecalho] = "[REDACTED]"
            return event

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            send_default_pii=False,
            before_send=filtrar_pii,
        )
    except Exception as e:
        logger.warning("Falha ao inicializar integração com GlitchTip/Sentry: %s", e)
