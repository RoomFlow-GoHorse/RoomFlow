from datetime import datetime, timezone

from sqlalchemy import select, update

from infrastructure.persistence.records import authorized_enrollments, pending_signups
from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.user_mapping import to_database_identity_id
from models.domain.entities.authorized_enrollment import normalize_registration_number
from models.domain.entities.pending_member_signup import PendingMemberSignup


class PostgresPendingSignupRepository:
    def __init__(self, transaction: PostgresTransaction):
        self._transaction = transaction

    def save(self, signup: PendingMemberSignup) -> None:
        with self._transaction.session() as session:
            session.execute(pending_signups.insert().values(
                token_digest=signup.token_digest,
                instituicao_id=to_database_identity_id(signup.institution_id),
                matricula_normalizada=normalize_registration_number(signup.registration_number),
                nome=signup.name, email=signup.email, senha_hash=signup.password_hash,
                convite_digest=signup.invitation_digest, expira_em=signup.expires_at,
            ))

    def find_by_digest(self, digest: str) -> PendingMemberSignup | None:
        lookup = select(pending_signups, authorized_enrollments.c.matricula).join(
            authorized_enrollments,
            (authorized_enrollments.c.instituicao_id == pending_signups.c.instituicao_id)
            & (authorized_enrollments.c.matricula_normalizada == pending_signups.c.matricula_normalizada),
        ).where(pending_signups.c.token_digest == digest, pending_signups.c.encerrado_em.is_(None))
        with self._transaction.session() as session:
            row = session.execute(lookup).first()
            if row is None:
                return None
            return PendingMemberSignup(
                row.token_digest, str(row.instituicao_id), row.matricula, row.nome,
                row.email, row.senha_hash, row.convite_digest, row.expira_em,
            )

    def delete(self, digest: str) -> None:
        self._close(pending_signups.c.token_digest == digest, datetime.now(timezone.utc))

    def delete_expired(self, now: datetime) -> None:
        self._close(pending_signups.c.expira_em <= now, now)

    def _close(self, condition, now: datetime) -> None:
        with self._transaction.session() as session:
            session.execute(update(pending_signups).where(
                condition, pending_signups.c.encerrado_em.is_(None),
            ).values(encerrado_em=now, senha_hash=None))
