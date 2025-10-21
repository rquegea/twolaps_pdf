"""
Add tipo_mercado to mercados

Revision ID: 20251021_add_tipo_mercado
Revises: 
Create Date: 2025-10-21 00:00:01
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251021_add_tipo_mercado'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add column with server_default to backfill existing rows
    op.add_column(
        'mercados',
        sa.Column('tipo_mercado', sa.String(length=50), nullable=False, server_default='FMCG')
    )
    # Add check constraint to enforce allowed values
    op.create_check_constraint(
        'check_tipo_mercado_valido',
        'mercados',
        "tipo_mercado IN ('FMCG', 'Health_Digital', 'Digital_SaaS', 'Services')"
    )
    # Add index for filtering by market type
    op.create_index('ix_mercados_tipo_mercado', 'mercados', ['tipo_mercado'])
    # Optional: remove server_default after backfill (kept to ease future inserts)


def downgrade() -> None:
    op.drop_index('ix_mercados_tipo_mercado', table_name='mercados')
    op.drop_constraint('check_tipo_mercado_valido', 'mercados', type_='check')
    op.drop_column('mercados', 'tipo_mercado')


