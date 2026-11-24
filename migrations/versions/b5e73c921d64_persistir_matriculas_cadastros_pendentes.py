"""Persist authorized enrollments and pending member signup."""

import sqlalchemy as sa
from alembic import op

revision = "b5e73c921d64"
down_revision = "52a4db81f603"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "matriculas_autorizadas",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("instituicao_id", sa.Integer(), sa.ForeignKey("instituicoes.id"), nullable=False),
        sa.Column("matricula", sa.String(50), nullable=False),
        sa.Column("matricula_normalizada", sa.Text(), nullable=False),
        sa.Column("nome", sa.String(150)),
        sa.Column("email", sa.String(255)),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("utilizado_por", sa.Integer()),
        sa.UniqueConstraint("instituicao_id", "matricula_normalizada", name="uq_matricula_autorizada_normalizada"),
        sa.CheckConstraint(
            "(status IN ('ativo', 'inativo') AND utilizado_por IS NULL) OR "
            "(status = 'utilizado' AND utilizado_por IS NOT NULL)",
            name="ck_matricula_autorizada_consumo",
        ),
        sa.ForeignKeyConstraint(
            ["utilizado_por", "instituicao_id"],
            ["usuario_instituicao.user_id", "usuario_instituicao.institution_id"],
            name="fk_matricula_autorizada_vinculo",
        ),
    )
    op.create_table(
        "cadastros_membro_pendentes",
        sa.Column("token_digest", sa.String(64), primary_key=True),
        sa.Column("instituicao_id", sa.Integer(), nullable=False),
        sa.Column("matricula_normalizada", sa.Text(), nullable=False),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("senha_hash", sa.String(255)),
        sa.Column("convite_digest", sa.String(64), sa.ForeignKey("convites_institucionais.digest"), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("encerrado_em", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["instituicao_id", "matricula_normalizada"],
            ["matriculas_autorizadas.instituicao_id", "matriculas_autorizadas.matricula_normalizada"],
            name="fk_cadastro_pendente_matricula",
        ),
        sa.CheckConstraint(
            "(encerrado_em IS NULL) = (senha_hash IS NOT NULL)", name="ck_cadastro_pendente_credencial",
        ),
    )
    op.create_index("ix_cadastro_pendente_expiracao", "cadastros_membro_pendentes", ["expira_em"])


def downgrade() -> None:
    raise RuntimeError("A revisão preserva as matrículas e os registros de cadastro.")
