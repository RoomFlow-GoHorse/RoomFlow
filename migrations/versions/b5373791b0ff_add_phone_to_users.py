"""add phone to users

Revision ID: b5373791b0ff
Revises: b82c7e4a91d3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b5373791b0ff'
down_revision: Union[str, None] = 'b82c7e4a91d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('phone', sa.String(length=20), nullable=True))

def downgrade() -> None:
    op.drop_column('usuarios', 'phone')
