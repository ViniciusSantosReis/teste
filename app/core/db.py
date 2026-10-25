"""Engine SQLAlchemy 2.0, Base declarativa, mixins de auditoria/soft delete e sessão."""

from collections.abc import Generator
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, create_engine, func
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    declarative_mixin,
    mapped_column,
    sessionmaker,
)

from app.core.config import get_settings

# Sem convenção explícita de nomes, o Alembic gera constraints que estouram
# os limites de caracteres do Oracle.
NAMING = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base declarativa para todas as tabelas do sistema."""

    metadata = MetaData(naming_convention=NAMING)


@declarative_mixin
class TimestampMixin:
    """Mixin com datas de criação e atualização em fuso horário UTC."""

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )


@declarative_mixin
class SoftDeleteMixin:
    """Nada é apagado fisicamente. O repositório filtra excluido_em IS NULL por padrão."""

    excluido_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )

    @property
    def ativo(self) -> bool:
        return self.excluido_em is None


settings = get_settings()

engine_kwargs: dict[str, Any] = {
    "pool_recycle": settings.DB_POOL_RECYCLE,
    "pool_pre_ping": True,
}

if "sqlite" not in settings.DATABASE_URL:
    engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW

engine = create_engine(
    settings.DATABASE_URL,
    **engine_kwargs,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency do FastAPI para obter sessão do banco de dados por requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
