"""Cria espaços, recursos e suas alocações."""

from alembic import op
import sqlalchemy as sa

revision = "5c91a6e3d204"
down_revision = "3f28b0a5c719"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'espacos',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('instituicao_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=150), nullable=False),
        sa.Column('tipo', sa.String(length=60), nullable=False),
        sa.Column('capacidade', sa.Integer(), nullable=False),
        sa.Column('localizacao', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('disponivel', 'bloqueado', name='status_espaco', native_enum=False, create_constraint=True), server_default='disponivel', nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('capacidade > 0', name='ck_espacos_capacidade'),
        sa.ForeignKeyConstraint(['instituicao_id'], ['instituicoes.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instituicao_id', 'id', name='uq_espacos_instituicao_id'),
        sa.UniqueConstraint('instituicao_id', 'nome', name='uq_espacos_instituicao_nome')
    )
    op.create_table(
        'recursos',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('instituicao_id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('quantidade_total', sa.Integer(), server_default='0', nullable=False),
        sa.Column('quantidade_indisponivel', sa.Integer(), server_default='0', nullable=False),
        sa.CheckConstraint('quantidade_total >= 0 AND quantidade_indisponivel BETWEEN 0 AND quantidade_total', name='ck_recursos_quantidades'),
        sa.ForeignKeyConstraint(['instituicao_id'], ['instituicoes.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instituicao_id', 'id', name='uq_recursos_instituicao_id'),
        sa.UniqueConstraint('instituicao_id', 'nome', name='uq_recursos_instituicao_nome')
    )
    op.create_table(
        'espaco_recursos',
        sa.Column('instituicao_id', sa.Integer(), nullable=False),
        sa.Column('espaco_id', sa.BigInteger(), nullable=False),
        sa.Column('recurso_id', sa.BigInteger(), nullable=False),
        sa.Column('quantidade', sa.Integer(), server_default='1', nullable=False),
        sa.CheckConstraint('quantidade > 0', name='ck_espaco_recursos_quantidade'),
        sa.ForeignKeyConstraint(['instituicao_id', 'espaco_id'], ['espacos.instituicao_id', 'espacos.id'], name='fk_espaco_recursos_espaco'),
        sa.ForeignKeyConstraint(['instituicao_id', 'recurso_id'], ['recursos.instituicao_id', 'recursos.id'], name='fk_espaco_recursos_recurso'),
        sa.PrimaryKeyConstraint('espaco_id', 'recurso_id')
    )


def downgrade() -> None:
    op.drop_table('espaco_recursos')
    op.drop_table('recursos')
    op.drop_table('espacos')
