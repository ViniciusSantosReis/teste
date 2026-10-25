"""Contexto de migrações do Alembic para a Intranet Decós.

Conecta ao Oracle Database via SQLAlchemy com a metadata de app.core.db.Base
e todos os modelos carregados.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.core.db import Base
# Importação dos modelos para registro na metadata
import app.modules.diretorio.models  # noqa: F401
import app.modules.identidade.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Executa migrações no modo 'offline' sem conexão ativa."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Executa migrações no modo 'online' conectando ao banco de dados."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()

def include_object(object, name, type_, reflected, compare_to):
    # Ignora a verificação automática conflitante do índice de aniversário no Oracle
    if type_ == "index" and name == "ix_usuarios_aniversario":
        return False
    return True


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
