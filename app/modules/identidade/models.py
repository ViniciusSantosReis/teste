"""Modelos SQLAlchemy do módulo de identidade — usuários e trilha de auditoria."""

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin
from app.modules.diretorio.models import Setor  # noqa: F401


class Usuario(Base, TimestampMixin):
    """Representa os colaboradores e administradores do hospital."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Identity(always=False), primary_key=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    nome_busca: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    id_setor: Mapped[int | None] = mapped_column(ForeignKey("setores.id"), nullable=True)
    cargo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ramal: Mapped[str | None] = mapped_column(String(10), nullable=True)
    data_nascimento: Mapped[date | None] = mapped_column(Date, nullable=True)
    data_admissao: Mapped[date | None] = mapped_column(Date, nullable=True)
    bio: Mapped[str | None] = mapped_column(String(300), nullable=True)
    foto_object_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Quatro papéis conforme requisito RD002 e especificação
    role: Mapped[str] = mapped_column(
        String(15),
        default="COLABORADOR",
        nullable=False,
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    desligado_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ultimo_login_em: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Colunas virtuais do Oracle: custo zero de armazenamento e indexáveis
    nasc_mes: Mapped[int | None] = mapped_column(
        Integer,
        Computed("EXTRACT(MONTH FROM data_nascimento)"),
        nullable=True,
    )
    nasc_dia: Mapped[int | None] = mapped_column(
        Integer,
        Computed("EXTRACT(DAY FROM data_nascimento)"),
        nullable=True,
    )

    setor = relationship("Setor", lazy="joined")

    __table_args__ = (
        CheckConstraint(
            "role IN ('COLABORADOR', 'RH', 'MARKETING', 'ADMIN')",
            name="ck_usuarios_role",
        ),
        Index("ix_usuarios_aniversario", "nasc_mes", "nasc_dia"),
        Index("ix_usuarios_setor", "id_setor", "ativo"),
        Index("ix_usuarios_busca", "nome_busca"),
    )


class Auditoria(Base):
    """Trilha de auditoria append-only para login, falhas e operações sensíveis."""

    __tablename__ = "auditoria"

    id: Mapped[int] = mapped_column(Identity(always=False), primary_key=True)
    entidade: Mapped[str] = mapped_column(String(40), nullable=False)
    entidade_id: Mapped[int] = mapped_column(Integer, nullable=False)
    acao: Mapped[str] = mapped_column(String(15), nullable=False)
    id_usuario: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"), nullable=True
    )
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    ip_origem: Mapped[str | None] = mapped_column(String(45), nullable=True)
    diff: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocorrido_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "acao IN ('CRIOU', 'ALTEROU', 'EXCLUIU', 'PUBLICOU', 'MODEROU', 'LOGIN', 'LOGIN_FALHA')",
            name="ck_auditoria_acao",
        ),
        Index("ix_auditoria_entidade", "entidade", "entidade_id", "ocorrido_em"),
        Index("ix_auditoria_usuario", "id_usuario", "ocorrido_em"),
    )
