"""Ponto de entrada do FastAPI da Intranet Hospitalar Decós Corporativa.

Configura aplicação, middlewares de observabilidade e segurança,
tratamento global de exceções e registro de rotas versionadas.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
import structlog

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.logging import configurar_logging
from app.core.observability import RequestIDMiddleware, configurar_observabilidade
from app.core.redis import redis_client
from app.modules.identidade.routers import router as auth_router
from app.shared.exceptions import IntranetException

settings = get_settings()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Gerencia eventos de inicialização e desligamento do ciclo de vida da API."""
    configurar_logging()
    configurar_observabilidade()
    logger.info(
        "Aplicação inicializada",
        ambiente=settings.APP_AMBIENTE,
        app=settings.APP_NOME,
    )
    yield
    logger.info("Aplicação sendo encerrada")


app = FastAPI(
    title=settings.APP_NOME,
    version="0.1.0",
    description="API RESTful corporativa para a Intranet Hospitalar Decós.",
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_AMBIENTE != "producao" else None,
    redoc_url="/redoc" if settings.APP_AMBIENTE != "producao" else None,
)

# ----------------- Middlewares -----------------
# 1. Rastreabilidade com Request ID
app.add_middleware(RequestIDMiddleware)

# 2. CORS para comunicação segura com frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGENS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)


# ----------------- Exception Handlers -----------------
@app.exception_handler(IntranetException)
async def intranet_exception_handler(
    request: Request,
    exc: IntranetException,
) -> JSONResponse:
    """Traduz exceções de domínio em respostas HTTP estruturadas."""
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.mensagem,
            "codigo": exc.codigo,
            "request_id": request_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Padroniza erros de validação do Pydantic (HTTP 422)."""
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Dados de requisição inválidos.",
            "codigo": "VALIDACAO_ERRO",
            "erros": exc.errors(),
            "request_id": request_id,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Intercepta exceções não tratadas evitando vazamento de tracebacks."""
    request_id = getattr(request.state, "request_id", None)
    logger.error("Erro interno não tratado", erro=str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Serviço temporariamente indisponível. Tente novamente mais tarde.",
            "codigo": "ERRO_INTERNO",
            "request_id": request_id,
        },
    )


# ----------------- Rotas de Verificação de Saúde (Health Checks) -----------------
health_router = APIRouter(prefix="/health", tags=["Saúde"])


@health_router.get("/live", status_code=status.HTTP_200_OK)
def liveness() -> dict[str, str]:
    """Liveness probe: indica se o processo da API está de pé."""
    return {"status": "ok"}


@health_router.get("/ready", status_code=status.HTTP_200_OK)
def readiness() -> dict[str, Any]:
    """Readiness probe: verifica conexão com Oracle e Redis."""
    status_db = "ok"
    status_redis = "ok"

    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1 FROM DUAL"))
    except Exception as e:
        logger.warning("Falha ao checar banco de dados no readiness", erro=str(e))
        status_db = "indisponivel"

    if redis_client:
        try:
            redis_client.ping()
        except Exception as e:
            logger.warning("Falha ao checar redis no readiness", erro=str(e))
            status_redis = "indisponivel"
    else:
        status_redis = "indisponivel"

    geral = "ready" if status_db == "ok" else "degraded"
    return {
        "status": geral,
        "database": status_db,
        "redis": status_redis,
    }


# ----------------- Agrupamento de Rotas da API v1 -----------------
api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(health_router)
api_v1.include_router(auth_router, prefix="/auth", tags=["Autenticação"])

app.include_router(api_v1)
