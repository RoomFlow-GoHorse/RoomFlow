from dataclasses import asdict

from sqlalchemy import select, update

from infrastructure.persistence.records import enrollment_previews
from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.user_mapping import to_database_identity_id
from models.domain.entities.authorized_enrollment import AuthorizedEnrollment
from models.domain.exceptions import ResourceNotFound


class PostgresEnrollmentPreviewRepository:
    def __init__(self, transaction: PostgresTransaction):
        self._transaction = transaction

    def save(self, preview_id, institution_id, enrollments, expires_at):
        with self._transaction.session() as session:
            session.execute(enrollment_previews.insert().values(
                id=preview_id, instituicao_id=to_database_identity_id(institution_id),
                matriculas=[asdict(item) for item in enrollments], expira_em=expires_at,
            ))

    def find(self, preview_id, institution_id, now):
        with self._transaction.session() as session:
            items = session.scalar(select(enrollment_previews.c.matriculas).where(
                enrollment_previews.c.id == preview_id,
                enrollment_previews.c.instituicao_id == to_database_identity_id(institution_id),
                enrollment_previews.c.confirmada_em.is_(None), enrollment_previews.c.expira_em > now,
            ))
            return tuple(AuthorizedEnrollment(**item) for item in items) if items is not None else None

    def consume(self, preview_id, institution_id, at):
        with self._transaction.session() as session:
            result = session.execute(update(enrollment_previews).where(
                enrollment_previews.c.id == preview_id,
                enrollment_previews.c.instituicao_id == to_database_identity_id(institution_id),
                enrollment_previews.c.confirmada_em.is_(None), enrollment_previews.c.expira_em > at,
            ).values(matriculas=None, confirmada_em=at))
            if not result.rowcount:
                raise ResourceNotFound("Prévia de importação não encontrada.")
