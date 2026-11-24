"""Add persisted reservation participants."""

import sqlalchemy as sa
from alembic import op


revision = "c8d15a6e2f91"
down_revision = "d74c2b9a1e60"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reserva_participantes",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("instituicao_id", sa.Integer(), nullable=False),
        sa.Column("reserva_id", sa.BigInteger(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("pendente", "confirmada", "recusada", name="status_participacao_reserva", native_enum=False, create_constraint=True), nullable=False, server_default="pendente"),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("respondido_em", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["instituicao_id", "reserva_id"], ["reservas.instituicao_id", "reservas.id"], name="fk_reserva_participantes_reserva", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id", "instituicao_id"], ["usuario_instituicao.user_id", "usuario_instituicao.institution_id"], name="fk_reserva_participantes_usuario"),
        sa.UniqueConstraint("reserva_id", "usuario_id", name="uq_reserva_participantes_reserva_usuario"),
    )
    op.create_index("ix_reserva_participantes_usuario", "reserva_participantes", ["instituicao_id", "usuario_id"])


def downgrade() -> None:
    op.drop_index("ix_reserva_participantes_usuario", table_name="reserva_participantes")
    op.drop_table("reserva_participantes")
