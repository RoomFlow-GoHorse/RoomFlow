from datetime import datetime

from sqlalchemy import select, update

from infrastructure.persistence.records import institution_invites
from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.user_mapping import to_database_identity_id
from models.domain.entities.institution_invite_code import InstitutionInviteCode


class PostgresInviteCodeRepository:
    def __init__(self, transaction: PostgresTransaction):
        self._transaction = transaction

    @staticmethod
    def _code(row) -> InstitutionInviteCode | None:
        if row is None:
            return None
        return InstitutionInviteCode(str(row.instituicao_id), row.digest, row.criado_em, row.revogado_em, row.id)

    def find_active(self, institution_id: str) -> InstitutionInviteCode | None:
        with self._transaction.session() as session:
            return self._code(session.execute(select(institution_invites).where(
                institution_invites.c.instituicao_id == to_database_identity_id(institution_id),
                institution_invites.c.revogado_em.is_(None),
            )).first())

    def find_active_by_digest(self, digest: str) -> InstitutionInviteCode | None:
        from models.database_models import Instituicao

        with self._transaction.session() as session:
            return self._code(session.execute(
                select(institution_invites)
                .join(Instituicao, Instituicao.id == institution_invites.c.instituicao_id)
                .where(institution_invites.c.digest == digest, institution_invites.c.revogado_em.is_(None),
                       Instituicao.status == "ativo")
            ).first())

    def replace(self, code: InstitutionInviteCode) -> None:
        with self._transaction.atomic(), self._transaction.session() as session:
            if session.scalar(select(institution_invites.c.id).where(institution_invites.c.digest == code.digest)):
                raise ValueError("Este código já foi usado.")
            self.revoke(code.institution_id, code.created_at)
            session.execute(institution_invites.insert().values(
                id=code.id, instituicao_id=to_database_identity_id(code.institution_id),
                digest=code.digest, criado_em=code.created_at,
            ))

    def revoke(self, institution_id: str, at: datetime) -> InstitutionInviteCode | None:
        with self._transaction.atomic(), self._transaction.session() as session:
            return self._code(session.execute(update(institution_invites).where(
                institution_invites.c.instituicao_id == to_database_identity_id(institution_id),
                institution_invites.c.revogado_em.is_(None),
            ).values(revogado_em=at).returning(institution_invites)).first())
