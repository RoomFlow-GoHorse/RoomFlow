from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from infrastructure.persistence.records import sessions
from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.user_mapping import to_database_identity_id
from models.domain.entities.user_session import UserSession


class PostgresSessionRepository:
    def __init__(self, transaction: PostgresTransaction):
        self._transaction = transaction

    def save(self, session: UserSession) -> None:
        statement = insert(sessions).values(
            token_digest=session.token_digest,
            usuario_id=to_database_identity_id(session.user_id),
            instituicao_id=to_database_identity_id(session.institution_id or ""),
            expira_em=session.expires_at,
            revogada_em=session.revoked_at,
        )
        with self._transaction.session() as connection:
            if session.revoked_at is None:
                connection.execute(statement)
            else:
                connection.execute(
                    update(sessions)
                    .where(sessions.c.token_digest == session.token_digest, sessions.c.revogada_em.is_(None))
                    .values(revogada_em=session.revoked_at)
                )

    def find_by_digest(self, token_digest: str) -> UserSession | None:
        with self._transaction.session() as session:
            row = session.execute(select(sessions).where(sessions.c.token_digest == token_digest)).first()
            if row is None:
                return None
            return UserSession(
                row.token_digest, str(row.usuario_id), row.expira_em,
                revoked_at=row.revogada_em, institution_id=str(row.instituicao_id),
            )

    def revoke_user(self, user_id: str, at: datetime, institution_id: str | None = None) -> None:
        statement = update(sessions).where(
            sessions.c.usuario_id == to_database_identity_id(user_id),
            sessions.c.revogada_em.is_(None), sessions.c.expira_em > at,
        )
        if institution_id is not None:
            statement = statement.where(sessions.c.instituicao_id == to_database_identity_id(institution_id))
        with self._transaction.session() as session:
            session.execute(statement.values(revogada_em=at))
