"""fix usuarios index names

Revision ID: e5b1d94c0274
Revises: d6efcf2ab1d6
Create Date: 2026-10-23 16:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5b1d94c0274'
down_revision = 'd6efcf2ab1d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove qualquer vestígio do índice antigo de busca no Oracle
    op.drop_index('ix_usuarios_nome_busca', table_name='usuarios', if_exists=True)
    
    # Assegura que o índice correto 'ix_usuarios_busca' está presente
    try:
        op.drop_index('ix_usuarios_busca', table_name='usuarios')
    except Exception:
        pass
    op.create_index('ix_usuarios_busca', 'usuarios', ['nome_busca'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_usuarios_busca', table_name='usuarios', if_exists=True)
    op.create_index('ix_usuarios_nome_busca', 'usuarios', ['nome_busca'], unique=False)