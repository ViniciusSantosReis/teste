"""Modelos SQLAlchemy do módulo diretorio — setores, colaboradores e ramais."""

from sqlalchemy import Boolean, Identity, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, TimestampMixin


class Setor(Base, TimestampMixin):
    """Representa os setores e departamentos do Hospital Decós."""

    __tablename__ = "setores"

    id: Mapped[int] = mapped_column(Identity(always=False), primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    nome_busca: Mapped[str] = mapped_column(String(100), nullable=False)
    sigla: Mapped[str | None] = mapped_column(String(15), nullable=True)
    ramal_geral: Mapped[str | None] = mapped_column(String(10), nullable=True)
    andar: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bloco: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("ix_setores_andar", "andar", "bloco"),
    )
