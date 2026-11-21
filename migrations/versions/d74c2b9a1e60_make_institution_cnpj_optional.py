"""Allow institution registrations without a CNPJ."""

import sqlalchemy as sa
from alembic import op


revision = "d74c2b9a1e60"
down_revision = "f13e57a9b40c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "instituicoes",
        "cnpj",
        existing_type=sa.String(length=18),
        nullable=True,
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_missing_cnpj = connection.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM instituicoes WHERE cnpj IS NULL)")
    ).scalar()
    if has_missing_cnpj:
        raise RuntimeError(
            "Não é possível tornar o CNPJ obrigatório enquanto houver instituições sem CNPJ."
        )
    op.alter_column(
        "instituicoes",
        "cnpj",
        existing_type=sa.String(length=18),
        nullable=False,
    )
