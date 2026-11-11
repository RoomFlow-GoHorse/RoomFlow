
"""create institutions and user-institution links <-- migration para gerar a tabela de instituições e de vínculo entre usuarios e instituições

Revision ID: b82c7e4a91d3 <-- ID da revisão
Revises: f4466d87fc91 <-- ID da revisão da qual esta revisão depende
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b82c7e4a91d3"
down_revision: Union[str, None] = "f4466d87fc91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Criação da tabela de instituições
    op.create_table("instituicoes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("cnpj", sa.String(18), nullable=False),
        sa.Column("institution_type", sa.String(60), nullable=False),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(2), nullable=True),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default=sa.text("'ativo'")),
        sa.UniqueConstraint("cnpj",name="uq_instituicoes_cnpj"),
    # TODO: Adicionar a criação de tabela de vínculo entre usuários e instituições
    
    )


def downgrade() -> None:
    op.drop_table("instituicoes")
