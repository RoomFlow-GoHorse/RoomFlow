
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    column,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.persistence import records  # noqa: F401 - register additive tables
from infrastructure.persistence import structure_records  # noqa: F401 - register structure tables
from infrastructure.persistence.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="ativo", nullable=False
    )

    # Campos antigos mantidos temporariamente para compatibilidade
    # com a estrutura atual do banco e a migração futura.
    
    # TODO: Após a migração para o novo modelo, remover estes campos.

    role: Mapped[str] = mapped_column(String(30), nullable=False)
    tipo_usuario_id: Mapped[int] = mapped_column(
        ForeignKey("tipos_usuario.id"), nullable=False
    )

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Vínculos deste usuário com instituições.
    institution_links: Mapped[list["UsuarioInstituicao"]] = relationship(
        back_populates="user"
    )


class TipoUsuario(Base):
    __tablename__ = "tipos_usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)


class Instituicao(Base):
    __tablename__ = "instituicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    cnpj: Mapped[str] = mapped_column(
        String(18), unique=True, nullable=False
    )
    institution_type: Mapped[str] = mapped_column(
        String(60), nullable=False
    )
    city: Mapped[str | None] = mapped_column(String(100), nullable=True) 
    state: Mapped[str | None] = mapped_column(String(2), nullable=True) #Campos alterados para permitir valores nulos
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default="ativo", server_default=text("'ativo'"), nullable=False #server_default para definir o valor no banco visto que apenas default define apenas no SQLAlchemy
    )

    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Vínculos dos usuários com a instituição.
    user_links: Mapped[list["UsuarioInstituicao"]] = relationship(
        back_populates="institution"
    )


class UsuarioInstituicao(Base):
    __tablename__ = "usuario_instituicao"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "institution_id",
            name="uq_usuario_instituicao_usuario_instituicao",
        ),
        UniqueConstraint(
            "institution_id",
            "registration_number",
            name="uq_usuario_instituicao_matricula",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id"), nullable=False
    )
    institution_id: Mapped[int] = mapped_column(
        ForeignKey("instituicoes.id"), nullable=False
    )

    # A matrícula faz parte de vínculo, pois pode variar
    # conforme a instituição. Eh opcional para permitir
    # vínculos de usários que não possuem matrícula.
    registration_number: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    # A função e situação são específicas deste vínculo.
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="ativo", server_default=text("'ativo'"), nullable=False #server_default para definir o valor no banco visto que apenas default define apenas no SQLAlchemy
    )

    user: Mapped["Usuario"] = relationship(
        back_populates="institution_links"
    )
    institution: Mapped["Instituicao"] = relationship(
        back_populates="user_links"
    )


class Espaco(Base):
    __tablename__ = "espacos"
    __table_args__ = (
        UniqueConstraint("instituicao_id", "nome", name="uq_espacos_instituicao_nome"),
        UniqueConstraint("instituicao_id", "id", name="uq_espacos_instituicao_id"),
        CheckConstraint("capacidade > 0", name="ck_espacos_capacidade"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instituicao_id: Mapped[int] = mapped_column(ForeignKey("instituicoes.id"))
    nome: Mapped[str] = mapped_column(String(150))
    tipo: Mapped[str] = mapped_column(String(60))
    capacidade: Mapped[int]
    localizacao: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        Enum("disponivel", "bloqueado", name="status_espaco", native_enum=False, create_constraint=True),
        server_default="disponivel",
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Recurso(Base):
    __tablename__ = "recursos"
    __table_args__ = (
        UniqueConstraint("instituicao_id", "nome", name="uq_recursos_instituicao_nome"),
        UniqueConstraint("instituicao_id", "id", name="uq_recursos_instituicao_id"),
        CheckConstraint(
            "quantidade_total >= 0 AND quantidade_indisponivel BETWEEN 0 AND quantidade_total",
            name="ck_recursos_quantidades",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instituicao_id: Mapped[int] = mapped_column(ForeignKey("instituicoes.id"))
    nome: Mapped[str] = mapped_column(String(100))
    quantidade_total: Mapped[int] = mapped_column(server_default="0")
    quantidade_indisponivel: Mapped[int] = mapped_column(server_default="0")


class EspacoRecurso(Base):
    __tablename__ = "espaco_recursos"
    __table_args__ = (
        ForeignKeyConstraint(
            ["instituicao_id", "espaco_id"], ["espacos.instituicao_id", "espacos.id"],
            name="fk_espaco_recursos_espaco",
        ),
        ForeignKeyConstraint(
            ["instituicao_id", "recurso_id"], ["recursos.instituicao_id", "recursos.id"],
            name="fk_espaco_recursos_recurso",
        ),
        CheckConstraint("quantidade > 0", name="ck_espaco_recursos_quantidade"),
    )

    instituicao_id: Mapped[int]
    espaco_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    recurso_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    quantidade: Mapped[int] = mapped_column(server_default="1")


class Reserva(Base):
    __tablename__ = "reservas"
    __table_args__ = (
        UniqueConstraint("instituicao_id", "id", name="uq_reservas_instituicao_id"),
        ForeignKeyConstraint(
            ["instituicao_id", "espaco_id"], ["espacos.instituicao_id", "espacos.id"],
            name="fk_reservas_espaco",
        ),
        ForeignKeyConstraint(
            ["solicitante_id", "instituicao_id"],
            ["usuario_instituicao.user_id", "usuario_instituicao.institution_id"],
            name="fk_reservas_solicitante",
        ),
        ForeignKeyConstraint(
            ["avaliado_por", "instituicao_id"],
            ["usuario_instituicao.user_id", "usuario_instituicao.institution_id"],
            name="fk_reservas_avaliador",
        ),
        CheckConstraint("fim > inicio", name="ck_reservas_periodo"),
        CheckConstraint("quantidade_participantes > 0", name="ck_reservas_participantes"),
        Index("ix_reservas_espaco_periodo", "espaco_id", "inicio", "fim"),
        Index("ix_reservas_solicitante_status", "solicitante_id", "status"),
        ExcludeConstraint(
            ("espaco_id", "="),
            (func.tstzrange(column("inicio"), column("fim"), "[)"), "&&"),
            where=text("status = 'aprovada'"),
            name="ex_reservas_aprovadas_periodo",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instituicao_id: Mapped[int]
    espaco_id: Mapped[int] = mapped_column(BigInteger)
    solicitante_id: Mapped[int]
    titulo: Mapped[str] = mapped_column(String(200))
    tipo: Mapped[str] = mapped_column(String(60))
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fim: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    quantidade_participantes: Mapped[int]
    justificativa: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        Enum("pendente", "aprovada", "rejeitada", "em_analise", "conflito", "cancelada",
             name="status_reserva", native_enum=False, create_constraint=True),
        server_default="pendente",
    )
    prioridade: Mapped[str] = mapped_column(
        Enum("baixa", "media", "alta", name="nivel_prioridade", native_enum=False, create_constraint=True),
        server_default="media",
    )
    avaliado_por: Mapped[int | None]
    avaliado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_decisao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConflitoReserva(Base):
    __tablename__ = "conflitos"
    __table_args__ = (
        UniqueConstraint("instituicao_id", "id", name="uq_conflitos_instituicao_id"),
        UniqueConstraint("reserva_a_id", "reserva_b_id", name="uq_conflitos_reservas"),
        ForeignKeyConstraint(
            ["instituicao_id", "reserva_a_id"], ["reservas.instituicao_id", "reservas.id"],
            name="fk_conflitos_reserva_a",
        ),
        ForeignKeyConstraint(
            ["instituicao_id", "reserva_b_id"], ["reservas.instituicao_id", "reservas.id"],
            name="fk_conflitos_reserva_b",
        ),
        ForeignKeyConstraint(
            ["resolvido_por", "instituicao_id"],
            ["usuario_instituicao.user_id", "usuario_instituicao.institution_id"],
            name="fk_conflitos_responsavel",
        ),
        CheckConstraint("reserva_a_id < reserva_b_id", name="ck_conflitos_ordem_reservas"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instituicao_id: Mapped[int]
    reserva_a_id: Mapped[int] = mapped_column(BigInteger)
    reserva_b_id: Mapped[int] = mapped_column(BigInteger)
    motivo: Mapped[str] = mapped_column(Text)
    gravidade: Mapped[str] = mapped_column(
        Enum("baixa", "media", "alta", name="nivel_prioridade", native_enum=False, create_constraint=True),
        server_default="media",
    )
    status: Mapped[str] = mapped_column(
        Enum("nao_resolvido", "em_analise", "resolvido", name="status_conflito",
             native_enum=False, create_constraint=True),
        server_default="nao_resolvido",
    )
    decisao: Mapped[str | None] = mapped_column(Text)
    resolvido_por: Mapped[int | None]
    resolvido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notificacao(Base):
    __tablename__ = "notificacoes"
    __table_args__ = (
        UniqueConstraint("instituicao_id", "id", name="uq_notificacoes_instituicao_id"),
        ForeignKeyConstraint(
            ["instituicao_id", "reserva_id"], ["reservas.instituicao_id", "reservas.id"],
            name="fk_notificacoes_reserva",
        ),
        ForeignKeyConstraint(
            ["instituicao_id", "conflito_id"], ["conflitos.instituicao_id", "conflitos.id"],
            name="fk_notificacoes_conflito",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instituicao_id: Mapped[int] = mapped_column(ForeignKey("instituicoes.id"))
    reserva_id: Mapped[int | None] = mapped_column(BigInteger)
    conflito_id: Mapped[int | None] = mapped_column(BigInteger)
    titulo: Mapped[str] = mapped_column(String(200))
    mensagem: Mapped[str] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(30))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DestinatarioNotificacao(Base):
    __tablename__ = "notificacao_destinatarios"
    __table_args__ = (
        ForeignKeyConstraint(
            ["instituicao_id", "notificacao_id"],
            ["notificacoes.instituicao_id", "notificacoes.id"],
            name="fk_notificacao_destinatarios_notificacao",
        ),
        ForeignKeyConstraint(
            ["usuario_id", "instituicao_id"],
            ["usuario_instituicao.user_id", "usuario_instituicao.institution_id"],
            name="fk_notificacao_destinatarios_usuario",
        ),
        Index("ix_notificacao_destinatarios_usuario_lida", "usuario_id", "lida_em"),
    )

    instituicao_id: Mapped[int]
    notificacao_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(primary_key=True)
    lida_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
