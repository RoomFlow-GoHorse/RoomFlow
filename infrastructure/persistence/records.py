from sqlalchemy import (
    CheckConstraint, Column, DateTime, ForeignKey, ForeignKeyConstraint, Index,
    Integer, String, Table, Text, UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import JSONB

from infrastructure.persistence.base import Base


sessions = Table(
    "sessoes_usuario", Base.metadata,
    Column("token_digest", String(64), primary_key=True),
    Column("usuario_id", Integer, nullable=False),
    Column("instituicao_id", Integer, nullable=False),
    Column("expira_em", DateTime(timezone=True), nullable=False),
    Column("revogada_em", DateTime(timezone=True)),
    ForeignKeyConstraint(
        ["usuario_id", "instituicao_id"],
        ["usuario_instituicao.user_id", "usuario_instituicao.institution_id"],
        name="fk_sessoes_usuario_vinculo",
    ),
    Index("ix_sessoes_usuario_vinculo", "usuario_id", "instituicao_id"),
)

audit_events = Table(
    "auditoria_administrativa", Base.metadata,
    Column("id", String(64), primary_key=True),
    Column("instituicao_id", Integer, ForeignKey("instituicoes.id"), nullable=False),
    Column("ator_id", Integer, ForeignKey("usuarios.id"), nullable=False),
    Column("ator_nome", String(150), nullable=False),
    Column("acao", String(80), nullable=False),
    Column("recurso_tipo", String(60), nullable=False),
    Column("recurso_id", String(100), nullable=False),
    Column("ocorreu_em", DateTime(timezone=True), nullable=False),
    Index("ix_auditoria_administrativa_instituicao_data", "instituicao_id", "ocorreu_em"),
)

institution_settings = Table(
    "configuracoes_instituicao", Base.metadata,
    Column("instituicao_id", Integer, ForeignKey("instituicoes.id"), primary_key=True),
    Column("endereco", String(240)),
    Column("fuso", String(60), nullable=False),
    Column("preferencias", JSONB, nullable=False),
)

institution_invites = Table(
    "convites_institucionais", Base.metadata,
    Column("id", String(64), primary_key=True),
    Column("instituicao_id", Integer, ForeignKey("instituicoes.id"), nullable=False),
    Column("digest", String(64), nullable=False, unique=True),
    Column("criado_em", DateTime(timezone=True), nullable=False),
    Column("revogado_em", DateTime(timezone=True)),
    Index("uq_convites_institucionais_ativo", "instituicao_id", unique=True,
          postgresql_where=text("revogado_em IS NULL")),
)

authorized_enrollments = Table(
    "matriculas_autorizadas", Base.metadata,
    Column("id", String(64), primary_key=True),
    Column("instituicao_id", Integer, ForeignKey("instituicoes.id"), nullable=False),
    Column("matricula", String(50), nullable=False),
    Column("matricula_normalizada", Text, nullable=False),
    Column("nome", String(150)),
    Column("email", String(255)),
    Column("status", String(12), nullable=False),
    Column("utilizado_por", Integer),
    UniqueConstraint("instituicao_id", "matricula_normalizada", name="uq_matricula_autorizada_normalizada"),
    CheckConstraint(
        "(status IN ('ativo', 'inativo') AND utilizado_por IS NULL) OR "
        "(status = 'utilizado' AND utilizado_por IS NOT NULL)",
        name="ck_matricula_autorizada_consumo",
    ),
    ForeignKeyConstraint(
        ["utilizado_por", "instituicao_id"],
        ["usuario_instituicao.user_id", "usuario_instituicao.institution_id"],
        name="fk_matricula_autorizada_vinculo",
    ),
)

pending_signups = Table(
    "cadastros_membro_pendentes", Base.metadata,
    Column("token_digest", String(64), primary_key=True),
    Column("instituicao_id", Integer, nullable=False),
    Column("matricula_normalizada", Text, nullable=False),
    Column("nome", String(150), nullable=False),
    Column("email", String(255), nullable=False),
    Column("senha_hash", String(255)),
    Column("convite_digest", String(64), ForeignKey("convites_institucionais.digest"), nullable=False),
    Column("expira_em", DateTime(timezone=True), nullable=False),
    Column("encerrado_em", DateTime(timezone=True)),
    ForeignKeyConstraint(
        ["instituicao_id", "matricula_normalizada"],
        ["matriculas_autorizadas.instituicao_id", "matriculas_autorizadas.matricula_normalizada"],
        name="fk_cadastro_pendente_matricula",
    ),
    CheckConstraint("(encerrado_em IS NULL) = (senha_hash IS NOT NULL)", name="ck_cadastro_pendente_credencial"),
    Index("ix_cadastro_pendente_expiracao", "expira_em"),
)

password_recoveries = Table(
    "recuperacoes_senha", Base.metadata,
    Column("token_digest", String(64), primary_key=True),
    Column("usuario_id", Integer, ForeignKey("usuarios.id"), nullable=False),
    Column("expira_em", DateTime(timezone=True), nullable=False),
    Column("encerrado_em", DateTime(timezone=True)),
    Index("uq_recuperacao_ativa_usuario", "usuario_id", unique=True,
          postgresql_where=text("encerrado_em IS NULL")),
)

enrollment_previews = Table(
    "previas_importacao_matricula", Base.metadata,
    Column("id", String(100), primary_key=True),
    Column("instituicao_id", Integer, ForeignKey("instituicoes.id"), nullable=False),
    Column("matriculas", JSONB),
    Column("expira_em", DateTime(timezone=True), nullable=False),
    Column("confirmada_em", DateTime(timezone=True)),
    Index("ix_previa_matricula_expiracao", "expira_em"),
)
