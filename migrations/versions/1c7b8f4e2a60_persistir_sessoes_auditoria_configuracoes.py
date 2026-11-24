"""Persist institutional sessions, audit events, and settings."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "1c7b8f4e2a60"
down_revision = "9d62e8a4b031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sessoes_usuario",
        sa.Column("token_digest", sa.String(64), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("instituicao_id", sa.Integer(), nullable=False),
        sa.Column("expira_em", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revogada_em", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["usuario_id", "instituicao_id"],
            ["usuario_instituicao.user_id", "usuario_instituicao.institution_id"],
            name="fk_sessoes_usuario_vinculo",
        ),
    )
    op.create_index("ix_sessoes_usuario_vinculo", "sessoes_usuario", ["usuario_id", "instituicao_id"])
    op.create_table(
        "auditoria_administrativa",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("instituicao_id", sa.Integer(), sa.ForeignKey("instituicoes.id"), nullable=False),
        sa.Column("ator_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("ator_nome", sa.String(150), nullable=False),
        sa.Column("acao", sa.String(80), nullable=False),
        sa.Column("recurso_tipo", sa.String(60), nullable=False),
        sa.Column("recurso_id", sa.String(100), nullable=False),
        sa.Column("ocorreu_em", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_auditoria_administrativa_instituicao_data",
        "auditoria_administrativa", ["instituicao_id", "ocorreu_em"],
    )
    op.create_table(
        "configuracoes_instituicao",
        sa.Column("instituicao_id", sa.Integer(), sa.ForeignKey("instituicoes.id"), primary_key=True),
        sa.Column("endereco", sa.String(240)),
        sa.Column("fuso", sa.String(60), nullable=False),
        sa.Column("preferencias", postgresql.JSONB(), nullable=False),
    )


def downgrade() -> None:
    raise RuntimeError("A revisão preserva sessões, auditoria e configurações persistidas.")
