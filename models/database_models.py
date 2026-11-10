
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from config.database import Base


class User(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
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

    # Vínculos deste usuário com instituições.
    institution_links: Mapped[list["UserInstitution"]] = relationship(
        back_populates="user"
    )


class UserType(Base):
    __tablename__ = "tipos_usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)


class Institution(Base):
    __tablename__ = "instituicoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    cnpj: Mapped[str] = mapped_column(
        String(18), unique=True, nullable=False
    )
    institution_type: Mapped[str] = mapped_column(
        String(60), nullable=False
    )
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), default="ativo", nullable=False
    )

    # Vínculos dos usuários com a instituição.
    user_links: Mapped[list["UserInstitution"]] = relationship(
        back_populates="institution"
    )


class UserInstitution(Base):
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
        String(30), default="ativo", nullable=False
    )

    user: Mapped["User"] = relationship(
        back_populates="institution_links"
    )
    institution: Mapped["Institution"] = relationship(
        back_populates="user_links"
    )
