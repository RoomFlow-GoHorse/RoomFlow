"""Persist institutional invitation digests."""

import sqlalchemy as sa
from alembic import op

revision = "52a4db81f603"
down_revision = "1c7b8f4e2a60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "convites_institucionais",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("instituicao_id", sa.Integer(), sa.ForeignKey("instituicoes.id"), nullable=False),
        sa.Column("digest", sa.String(64), nullable=False, unique=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revogado_em", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "uq_convites_institucionais_ativo", "convites_institucionais", ["instituicao_id"],
        unique=True, postgresql_where=sa.text("revogado_em IS NULL"),
    )


def downgrade() -> None:
    raise RuntimeError("A revisão preserva os convites institucionais persistidos.")
