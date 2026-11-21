from dataclasses import asdict

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert

from infrastructure.persistence.records import institution_settings
from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.user_mapping import to_database_identity_id
from models.database_models import Instituicao
from models.domain.entities.institution import (
    ConflictPreferences, Institution, InstitutionPreferences,
    NotificationPreferences, ReservationPreferences,
)
from models.domain.exceptions import DuplicateResource, ResourceNotFound
from models.domain.identity_normalization import normalize_cnpj


def _to_institution(row: Instituicao, settings) -> Institution:
    data = settings.preferencias if settings is not None else {}
    preferences = InstitutionPreferences(
        reservations=ReservationPreferences(**data.get("reservations", {})),
        conflicts=ConflictPreferences(**data.get("conflicts", {})),
        notifications=NotificationPreferences(**data.get("notifications", {})),
    )
    return Institution(
        id=str(row.id), name=row.name,
        cnpj=normalize_cnpj(row.cnpj) if row.cnpj else None,
        institution_type=row.institution_type, city=row.city, state=row.state,
        phone=row.phone, email=row.email,
        address=settings.endereco if settings is not None else None,
        timezone=settings.fuso if settings is not None else "America/Sao_Paulo",
        preferences=preferences,
    )


class PostgresInstitutionRepository:
    def __init__(self, transaction: PostgresTransaction):
        self._transaction = transaction

    def find_by_id(self, institution_id: str) -> Institution | None:
        try:
            database_id = to_database_identity_id(institution_id)
        except ValueError:
            return None
        with self._transaction.session() as session:
            row = session.get(Instituicao, database_id)
            return self._read_settings(session, row) if row is not None else None

    def find_by_cnpj(self, cnpj: str) -> Institution | None:
        lookup = select(Instituicao).where(
            func.regexp_replace(Instituicao.cnpj, "[^0-9]", "", "g") == normalize_cnpj(cnpj)
        )
        with self._transaction.session() as session:
            matches = session.scalars(lookup.order_by(Instituicao.id).limit(2)).all()
            if len(matches) > 1:
                raise DuplicateResource("Há mais de uma instituição com este CNPJ normalizado.")
            return self._read_settings(session, matches[0]) if matches else None

    def add(self, institution: Institution) -> Institution:
        cnpj = normalize_cnpj(institution.cnpj or "")
        if cnpj and (len(cnpj) != 14 or not cnpj.isascii()):
            raise ValueError("Informe um CNPJ com 14 dígitos de 0 a 9.")
        with self._transaction.atomic(), self._transaction.session() as session:
            if cnpj and self.find_by_cnpj(cnpj) is not None:
                raise DuplicateResource("Já existe uma instituição com este CNPJ.")
            row = Instituicao(cnpj=cnpj or None)
            self._update_fields(row, institution)
            session.add(row)
            session.flush()
            self._save_settings(session, row.id, institution)
            return self._read_settings(session, row)

    def save(self, institution: Institution) -> None:
        with self._transaction.atomic(), self._transaction.session() as session:
            row = session.get(Instituicao, to_database_identity_id(institution.id))
            if row is None:
                raise ResourceNotFound("Instituição não encontrada.")
            self._update_fields(row, institution)
            self._save_settings(session, row.id, institution)

    def list_all(self) -> tuple[Institution, ...]:
        with self._transaction.session() as session:
            return tuple(
                self._read_settings(session, row)
                for row in session.scalars(select(Instituicao).order_by(Instituicao.id))
            )

    def remove(self, institution_id: str) -> None:
        with self._transaction.atomic(), self._transaction.session() as session:
            database_id = to_database_identity_id(institution_id)
            session.execute(delete(institution_settings).where(institution_settings.c.instituicao_id == database_id))
            session.execute(delete(Instituicao).where(Instituicao.id == database_id))

    @staticmethod
    def _read_settings(session, row: Instituicao) -> Institution:
        settings = session.execute(
            select(institution_settings).where(institution_settings.c.instituicao_id == row.id)
        ).first()
        return _to_institution(row, settings)

    @staticmethod
    def _update_fields(row: Instituicao, institution: Institution) -> None:
        for field, limit in (("name", 150), ("institution_type", 60), ("phone", 20)):
            if len(getattr(institution, field) or "") > limit:
                raise ValueError(f"O campo {field} aceita até {limit} caracteres no banco.")
        row.name = institution.name
        row.institution_type = institution.institution_type or row.institution_type
        row.city = institution.city
        row.state = institution.state
        row.phone = institution.phone
        row.email = institution.email

    @staticmethod
    def _save_settings(session, institution_id: int, institution: Institution) -> None:
        values = dict(
            endereco=institution.address, fuso=institution.timezone,
            preferencias=asdict(institution.preferences),
        )
        session.execute(insert(institution_settings).values(instituicao_id=institution_id, **values)
            .on_conflict_do_update(index_elements=[institution_settings.c.instituicao_id], set_=values))
