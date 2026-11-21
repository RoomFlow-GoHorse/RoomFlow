from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column, DateTime, Float, ForeignKey, ForeignKeyConstraint,
    Index, Integer, LargeBinary, String, Table, UniqueConstraint, text,
)

from infrastructure.persistence.base import Base

metadata = Base.metadata

predios = Table(
    "predios", metadata,
    Column("id", String(64), primary_key=True),
    Column("instituicao_id", Integer, ForeignKey("instituicoes.id"), nullable=False),
    Column("nome", String(120), nullable=False),
    Column("ativo", Boolean, server_default=text("true"), nullable=False),
    UniqueConstraint("instituicao_id", "id", name="uq_predio_instituicao_id"),
    UniqueConstraint("instituicao_id", "nome", name="uq_predio_instituicao_nome"),
)
andares = Table(
    "andares", metadata,
    Column("id", String(64), primary_key=True),
    Column("instituicao_id", Integer, nullable=False),
    Column("predio_id", String(64), nullable=False),
    Column("nome", String(120), nullable=False),
    Column("ativo", Boolean, server_default=text("true"), nullable=False),
    ForeignKeyConstraint(["instituicao_id", "predio_id"], ["predios.instituicao_id", "predios.id"],
                         name="fk_andar_predio"),
    UniqueConstraint("instituicao_id", "id", name="uq_andar_instituicao_id"),
    UniqueConstraint("predio_id", "nome", name="uq_andar_predio_nome"),
)
estrutura_espaco = Table(
    "estrutura_espaco", metadata,
    Column("espaco_id", BigInteger, primary_key=True, autoincrement=False),
    Column("instituicao_id", Integer, nullable=False),
    Column("andar_id", String(64)),
    Column("ativo", Boolean, server_default=text("true"), nullable=False),
    ForeignKeyConstraint(["instituicao_id", "espaco_id"], ["espacos.instituicao_id", "espacos.id"],
                         name="fk_estrutura_espaco"),
    ForeignKeyConstraint(["instituicao_id", "andar_id"], ["andares.instituicao_id", "andares.id"],
                         name="fk_estrutura_andar"),
    Index("ix_estrutura_espaco_andar", "andar_id"),
)
ativacao_recurso = Table(
    "ativacao_recurso", metadata,
    Column("recurso_id", BigInteger, primary_key=True, autoincrement=False),
    Column("instituicao_id", Integer, nullable=False),
    Column("ativo", Boolean, server_default=text("true"), nullable=False),
    ForeignKeyConstraint(["instituicao_id", "recurso_id"], ["recursos.instituicao_id", "recursos.id"],
                         name="fk_ativacao_recurso"),
)
arquivos_planta = Table(
    "arquivos_planta", metadata,
    Column("chave", String(100), primary_key=True),
    Column("conteudo", LargeBinary, nullable=False),
    Column("retirado_em", DateTime(timezone=True)),
)
plantas_andar = Table(
    "plantas_andar", metadata,
    Column("id", String(64), primary_key=True),
    Column("instituicao_id", Integer, nullable=False),
    Column("andar_id", String(64), nullable=False),
    Column("arquivo_chave", String(100), ForeignKey("arquivos_planta.chave"), nullable=False),
    Column("nome", String(255), nullable=False),
    Column("tipo_midia", String(60), nullable=False),
    Column("checksum", String(64), nullable=False),
    Column("removida_em", DateTime(timezone=True)),
    ForeignKeyConstraint(["instituicao_id", "andar_id"], ["andares.instituicao_id", "andares.id"],
                         name="fk_planta_andar"),
    UniqueConstraint("instituicao_id", "id", name="uq_planta_instituicao_id"),
    Index("uq_planta_ativa_andar", "andar_id", unique=True, postgresql_where=text("removida_em IS NULL")),
)
posicoes_planta = Table(
    "posicoes_planta", metadata,
    Column("planta_id", String(64), primary_key=True),
    Column("espaco_id", BigInteger, primary_key=True),
    Column("instituicao_id", Integer, nullable=False),
    Column("x", Float, nullable=False),
    Column("y", Float, nullable=False),
    Column("ativo", Boolean, server_default=text("true"), nullable=False),
    ForeignKeyConstraint(["instituicao_id", "planta_id"], ["plantas_andar.instituicao_id", "plantas_andar.id"],
                         name="fk_posicao_planta"),
    ForeignKeyConstraint(["instituicao_id", "espaco_id"], ["espacos.instituicao_id", "espacos.id"],
                         name="fk_posicao_espaco"),
    CheckConstraint("x BETWEEN 0 AND 100 AND y BETWEEN 0 AND 100", name="ck_posicao_coordenadas"),
)
