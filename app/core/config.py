"""Pydantic Settings — carrega e valida TODA variável de ambiente descrita no .env.example."""


"""Configurações da aplicação utilizando Pydantic Settings.

Carrega e valida as variáveis de ambiente definidas no arquivo .env
conforme o padrão estabelecido em .env.example e PROJETO.md.
"""

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações globais e tipadas da Intranet Decós API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---------- Aplicação ----------
    APP_NOME: str = "Intranet Decós"
    APP_AMBIENTE: str = "dev"  # dev | homologacao | producao
    APP_DEBUG: bool = True
    UVICORN_WORKERS: int = 4
    APP_URL: str = "http://localhost:5173"
    SECRET_KEY: str = "troque-isto-em-producao"
    CORS_ORIGENS: list[str] = ["http://localhost:5173"]

    @field_validator("CORS_ORIGENS", mode="before")
    @classmethod
    def formatar_cors(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [origem.strip() for origem in v.split(",") if origem.strip()]
        if isinstance(v, list):
            return [str(origem).strip() for origem in v]
        return ["http://localhost:5173"]

    # ---------- Banco ----------
    DATABASE_URL: str = (
        "oracle+oracledb://INTRANET_APP:senha@oracle:1521/?service_name=FREEPDB1"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 1800

    # ---------- Autenticação ----------
    JWT_ACCESS_MINUTOS: int = 15
    JWT_REFRESH_DIAS: int = 7
    LOGIN_MAX_TENTATIVAS: int = 5
    JWT_ALGORITMO: str = "HS256"

    # ---------- Storage ----------
    S3_ENDPOINT: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_REGIAO: str = "us-east-1"
    S3_BUCKET_MIDIA: str = "decos-midia"
    S3_BUCKET_DOCUMENTOS: str = "decos-documentos"
    S3_BUCKET_AVATARES: str = "decos-avatares"
    S3_BUCKET_BACKUP: str = "decos-backup"
    UPLOAD_MAX_MB_IMAGEM: int = 10
    UPLOAD_MAX_MB_ARQUIVO: int = 25
    URL_ASSINADA_MINUTOS: int = 60

    # ---------- Redis ----------
    REDIS_URL: str = "redis://redis:6379/0"

    # ---------- Observabilidade ----------
    SENTRY_DSN: str | None = None
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    LOG_LEVEL: str = "INFO"
    LOG_FORMATO: str = "json"

    # ---------- Moderação ----------
    MODERACAO_PREVIA: bool = False
    DENUNCIAS_PARA_REVISAO: int = 3

    # ---------- E-mail (SMTP interno) ----------
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USUARIO: str | None = None
    SMTP_SENHA: str | None = None
    SMTP_REMETENTE: str = "intranet@decos.local"


@lru_cache
def get_settings() -> Settings:
    """Retorna instância única (singleton em cache) das configurações."""
    return Settings()
