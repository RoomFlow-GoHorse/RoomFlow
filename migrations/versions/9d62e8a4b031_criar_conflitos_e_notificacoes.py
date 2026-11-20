"""Cria conflitos de reservas e notificações."""

from alembic import op
import sqlalchemy as sa

revision = "9d62e8a4b031"
down_revision = "7a4e9d2c6f10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'conflitos',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('instituicao_id', sa.Integer(), nullable=False),
        sa.Column('reserva_a_id', sa.BigInteger(), nullable=False),
        sa.Column('reserva_b_id', sa.BigInteger(), nullable=False),
        sa.Column('motivo', sa.Text(), nullable=False),
        sa.Column('gravidade', sa.Enum('baixa', 'media', 'alta', name='nivel_prioridade', native_enum=False, create_constraint=True), server_default='media', nullable=False),
        sa.Column('status', sa.Enum('nao_resolvido', 'em_analise', 'resolvido', name='status_conflito', native_enum=False, create_constraint=True), server_default='nao_resolvido', nullable=False),
        sa.Column('decisao', sa.Text(), nullable=True),
        sa.Column('resolvido_por', sa.Integer(), nullable=True),
        sa.Column('resolvido_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('reserva_a_id < reserva_b_id', name='ck_conflitos_ordem_reservas'),
        sa.ForeignKeyConstraint(['instituicao_id', 'reserva_a_id'], ['reservas.instituicao_id', 'reservas.id'], name='fk_conflitos_reserva_a'),
        sa.ForeignKeyConstraint(['instituicao_id', 'reserva_b_id'], ['reservas.instituicao_id', 'reservas.id'], name='fk_conflitos_reserva_b'),
        sa.ForeignKeyConstraint(['resolvido_por', 'instituicao_id'], ['usuario_instituicao.user_id', 'usuario_instituicao.institution_id'], name='fk_conflitos_responsavel'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instituicao_id', 'id', name='uq_conflitos_instituicao_id'),
        sa.UniqueConstraint('reserva_a_id', 'reserva_b_id', name='uq_conflitos_reservas')
    )
    op.create_table(
        'notificacoes',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('instituicao_id', sa.Integer(), nullable=False),
        sa.Column('reserva_id', sa.BigInteger(), nullable=True),
        sa.Column('conflito_id', sa.BigInteger(), nullable=True),
        sa.Column('titulo', sa.String(length=200), nullable=False),
        sa.Column('mensagem', sa.Text(), nullable=False),
        sa.Column('categoria', sa.String(length=30), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instituicao_id', 'conflito_id'], ['conflitos.instituicao_id', 'conflitos.id'], name='fk_notificacoes_conflito'),
        sa.ForeignKeyConstraint(['instituicao_id', 'reserva_id'], ['reservas.instituicao_id', 'reservas.id'], name='fk_notificacoes_reserva'),
        sa.ForeignKeyConstraint(['instituicao_id'], ['instituicoes.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instituicao_id', 'id', name='uq_notificacoes_instituicao_id')
    )
    op.create_table(
        'notificacao_destinatarios',
        sa.Column('instituicao_id', sa.Integer(), nullable=False),
        sa.Column('notificacao_id', sa.BigInteger(), nullable=False),
        sa.Column('usuario_id', sa.Integer(), nullable=False),
        sa.Column('lida_em', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['instituicao_id', 'notificacao_id'], ['notificacoes.instituicao_id', 'notificacoes.id'], name='fk_notificacao_destinatarios_notificacao'),
        sa.ForeignKeyConstraint(['usuario_id', 'instituicao_id'], ['usuario_instituicao.user_id', 'usuario_instituicao.institution_id'], name='fk_notificacao_destinatarios_usuario'),
        sa.PrimaryKeyConstraint('notificacao_id', 'usuario_id')
    )
    op.create_index('ix_notificacao_destinatarios_usuario_lida', 'notificacao_destinatarios', ['usuario_id', 'lida_em'], unique=False)


def downgrade() -> None:
    op.drop_table('notificacao_destinatarios')
    op.drop_table('notificacoes')
    op.drop_table('conflitos')
