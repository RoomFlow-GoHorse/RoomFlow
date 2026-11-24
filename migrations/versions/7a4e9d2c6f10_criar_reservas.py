"""Cria reservas e aplica as regras de horário e capacidade."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "7a4e9d2c6f10"
down_revision = "5c91a6e3d204"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.create_table(
        'reservas',
        sa.Column('id', sa.BigInteger(), nullable=False),
        sa.Column('instituicao_id', sa.Integer(), nullable=False),
        sa.Column('espaco_id', sa.BigInteger(), nullable=False),
        sa.Column('solicitante_id', sa.Integer(), nullable=False),
        sa.Column('titulo', sa.String(length=200), nullable=False),
        sa.Column('tipo', sa.String(length=60), nullable=False),
        sa.Column('inicio', sa.DateTime(timezone=True), nullable=False),
        sa.Column('fim', sa.DateTime(timezone=True), nullable=False),
        sa.Column('quantidade_participantes', sa.Integer(), nullable=False),
        sa.Column('justificativa', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('pendente', 'aprovada', 'rejeitada', 'em_analise', 'conflito', 'cancelada', name='status_reserva', native_enum=False, create_constraint=True), server_default='pendente', nullable=False),
        sa.Column('prioridade', sa.Enum('baixa', 'media', 'alta', name='nivel_prioridade', native_enum=False, create_constraint=True), server_default='media', nullable=False),
        sa.Column('avaliado_por', sa.Integer(), nullable=True),
        sa.Column('avaliado_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('motivo_decisao', sa.Text(), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        postgresql.ExcludeConstraint((sa.column('espaco_id'), '='), (sa.text("tstzrange(inicio, fim, '[)')"), '&&'), where=sa.text("status = 'aprovada'"), using='gist', name='ex_reservas_aprovadas_periodo'),
        sa.CheckConstraint('fim > inicio', name='ck_reservas_periodo'),
        sa.CheckConstraint('quantidade_participantes > 0', name='ck_reservas_participantes'),
        sa.ForeignKeyConstraint(['avaliado_por', 'instituicao_id'], ['usuario_instituicao.user_id', 'usuario_instituicao.institution_id'], name='fk_reservas_avaliador'),
        sa.ForeignKeyConstraint(['instituicao_id', 'espaco_id'], ['espacos.instituicao_id', 'espacos.id'], name='fk_reservas_espaco'),
        sa.ForeignKeyConstraint(['solicitante_id', 'instituicao_id'], ['usuario_instituicao.user_id', 'usuario_instituicao.institution_id'], name='fk_reservas_solicitante'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instituicao_id', 'id', name='uq_reservas_instituicao_id')
    )
    op.create_index('ix_reservas_espaco_periodo', 'reservas', ['espaco_id', 'inicio', 'fim'], unique=False)
    op.create_index('ix_reservas_solicitante_status', 'reservas', ['solicitante_id', 'status'], unique=False)

    op.execute("""
        CREATE FUNCTION roomflow_validar_capacidade_reserva() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE
            limite integer;
        BEGIN
            IF NEW.status IN ('cancelada', 'rejeitada') THEN
                RETURN NEW;
            END IF;
            SELECT capacidade INTO limite FROM espacos
                WHERE id = NEW.espaco_id AND instituicao_id = NEW.instituicao_id
                FOR SHARE;
            IF NEW.quantidade_participantes > limite THEN
                RAISE EXCEPTION 'Quantidade de participantes excede a capacidade do espaço'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER validar_capacidade_reserva
        BEFORE INSERT OR UPDATE OF espaco_id, instituicao_id, quantidade_participantes, status, fim
        ON reservas FOR EACH ROW EXECUTE FUNCTION roomflow_validar_capacidade_reserva()
    """)
    op.execute("""
        CREATE FUNCTION roomflow_validar_reducao_capacidade() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM reservas
                WHERE espaco_id = NEW.id
                  AND fim > statement_timestamp()
                  AND status NOT IN ('cancelada', 'rejeitada')
                  AND quantidade_participantes > NEW.capacidade
            ) THEN
                RAISE EXCEPTION 'A nova capacidade é menor que a quantidade de participantes de uma reserva vigente'
                    USING ERRCODE = 'check_violation';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER validar_reducao_capacidade
        BEFORE UPDATE OF capacidade ON espacos FOR EACH ROW
        WHEN (NEW.capacidade < OLD.capacidade)
        EXECUTE FUNCTION roomflow_validar_reducao_capacidade()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER validar_reducao_capacidade ON espacos")
    op.execute("DROP FUNCTION roomflow_validar_reducao_capacidade()")
    op.drop_table('reservas')
    op.execute("DROP FUNCTION roomflow_validar_capacidade_reserva()")
