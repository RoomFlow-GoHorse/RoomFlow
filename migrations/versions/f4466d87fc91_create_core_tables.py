"""create user types and users

Revision ID: f4466d87fc91
Revises: 
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f4466d87fc91'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tipos_usuario",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(30), nullable=False),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column(
            "tipo_usuario_id",
            sa.Integer(),
            sa.ForeignKey("tipos_usuario.id"),
            nullable=False,
        ),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_table("usuarios")
    op.drop_table("tipos_usuario")
