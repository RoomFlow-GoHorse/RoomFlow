"""Record institutional room blocks and retain their reasons after reopening."""

import sqlalchemy as sa
from alembic import op


revision = "a63dfec41897"
down_revision = "72fb19e406ac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bloqueios_espaco",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("instituicao_id", sa.Integer, nullable=False),
        sa.Column("espaco_id", sa.BigInteger, nullable=False),
        sa.Column("responsavel_id", sa.Integer, nullable=False),
        sa.Column("motivo", sa.String(500), nullable=False),
        sa.Column("bloqueado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("desbloqueado_em", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["instituicao_id", "espaco_id"], ["espacos.instituicao_id", "espacos.id"], name="fk_bloqueio_espaco",
        ),
        sa.ForeignKeyConstraint(
            ["responsavel_id", "instituicao_id"],
            ["usuario_instituicao.user_id", "usuario_instituicao.institution_id"],
            name="fk_bloqueio_responsavel",
        ),
        sa.CheckConstraint("length(btrim(motivo)) > 0", name="ck_bloqueio_motivo"),
        sa.CheckConstraint("desbloqueado_em >= bloqueado_em", name="ck_bloqueio_periodo"),
    )
    op.create_index(
        "uq_bloqueio_espaco_aberto", "bloqueios_espaco", ["espaco_id"],
        unique=True, postgresql_where=sa.text("desbloqueado_em IS NULL"),
    )


def downgrade() -> None:
    raise RuntimeError("A revisão preserva o histórico de bloqueios.")
