"""Adiciona datas de criação aos usuários e às instituições."""

from alembic import op
import sqlalchemy as sa

revision = "3f28b0a5c719"
down_revision = "b5373791b0ff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('instituicoes', sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))


def downgrade() -> None:
    op.drop_column('instituicoes', 'criado_em')
    op.drop_column('usuarios', 'criado_em')
