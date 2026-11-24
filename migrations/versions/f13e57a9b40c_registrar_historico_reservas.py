"""Registra avaliações, alterações e cancelamentos de reservas."""

import sqlalchemy as sa
from alembic import op


revision = "f13e57a9b40c"
down_revision = "a63dfec41897"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "historico_reservas",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("instituicao_id", sa.Integer, nullable=False),
        sa.Column("reserva_id", sa.BigInteger, nullable=False),
        sa.Column("acao", sa.String(24), nullable=False),
        sa.Column("status_anterior", sa.String(12)),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("ocorreu_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ator_id", sa.Integer),
        sa.Column("ator_nome", sa.String(150)),
        sa.Column("motivo", sa.String(600)),
        sa.ForeignKeyConstraint(
            ["instituicao_id", "reserva_id"], ["reservas.instituicao_id", "reservas.id"],
            name="fk_historico_reserva",
        ),
        sa.ForeignKeyConstraint(
            ["ator_id", "instituicao_id"], ["usuario_instituicao.user_id", "usuario_instituicao.institution_id"],
            name="fk_historico_reserva_ator",
        ),
    )
    op.create_index("ix_historico_reservas_reserva", "historico_reservas", ["instituicao_id", "reserva_id", "id"])


def downgrade() -> None:
    raise RuntimeError("A revisão preserva o histórico de reservas.")
