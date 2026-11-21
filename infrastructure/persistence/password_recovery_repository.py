from sqlalchemy import update

from infrastructure.persistence.records import password_recoveries
from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.user_mapping import to_database_identity_id


class PostgresPasswordRecoveryRepository:
    def __init__(self, transaction: PostgresTransaction):
        self._transaction = transaction

    def issue(self, digest, user_id, expires_at, now):
        database_id = to_database_identity_id(user_id)
        with self._transaction.session() as session:
            session.execute(update(password_recoveries).where(
                password_recoveries.c.usuario_id == database_id, password_recoveries.c.encerrado_em.is_(None),
            ).values(encerrado_em=now))
            session.execute(password_recoveries.insert().values(
                token_digest=digest, usuario_id=database_id, expira_em=expires_at,
            ))

    def consume(self, digest, now):
        with self._transaction.session() as session:
            user_id = session.scalar(update(password_recoveries).where(
                password_recoveries.c.token_digest == digest, password_recoveries.c.encerrado_em.is_(None),
                password_recoveries.c.expira_em > now,
            ).values(encerrado_em=now).returning(password_recoveries.c.usuario_id))
            return str(user_id) if user_id is not None else None
