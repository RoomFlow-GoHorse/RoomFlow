"""Persist password recovery and enrollment import previews."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "72fb19e406ac"
down_revision = "e11ca39f8a67"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recuperacoes_senha",
        sa.Column("token_digest", sa.String(64), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("encerrado_em", sa.DateTime(timezone=True)),
    )
    op.create_index("uq_recuperacao_ativa_usuario", "recuperacoes_senha", ["usuario_id"],
                    unique=True, postgresql_where=sa.text("encerrado_em IS NULL"))
    op.create_table(
        "previas_importacao_matricula",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("instituicao_id", sa.Integer(), sa.ForeignKey("instituicoes.id"), nullable=False),
        sa.Column("matriculas", postgresql.JSONB()),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmada_em", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_previa_matricula_expiracao", "previas_importacao_matricula", ["expira_em"])


def downgrade() -> None:
    raise RuntimeError("A revisão preserva os registros de recuperação e importação.")
