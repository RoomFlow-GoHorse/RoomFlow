from datetime import datetime

from sqlalchemy import select

from infrastructure.persistence.records import audit_events
from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.user_mapping import to_database_identity_id
from models.domain.entities.admin_audit_event import AdminAuditAction, AdminAuditEvent


class PostgresAdminAuditRepository:
    def __init__(self, transaction: PostgresTransaction):
        self._transaction = transaction

    def append(self, event: AdminAuditEvent) -> None:
        with self._transaction.session() as session:
            session.execute(audit_events.insert().values(
                id=event.id, instituicao_id=to_database_identity_id(event.institution_id),
                ator_id=to_database_identity_id(event.actor_user_id), ator_nome=event.actor_name,
                acao=event.action.value, recurso_tipo=event.resource_type,
                recurso_id=event.resource_id, ocorreu_em=event.occurred_at,
            ))

    def list_for_institution(
        self, institution_id: str, start_at: datetime | None = None,
        end_at: datetime | None = None, action: AdminAuditAction | None = None,
        actor_user_id: str | None = None, limit: int = 200,
    ) -> tuple[AdminAuditEvent, ...]:
        statement = select(audit_events).where(
            audit_events.c.instituicao_id == to_database_identity_id(institution_id)
        )
        if start_at is not None:
            statement = statement.where(audit_events.c.ocorreu_em >= start_at)
        if end_at is not None:
            statement = statement.where(audit_events.c.ocorreu_em <= end_at)
        if action is not None:
            statement = statement.where(audit_events.c.acao == action.value)
        if actor_user_id is not None:
            try:
                actor_id = to_database_identity_id(actor_user_id)
            except ValueError:
                return ()
            statement = statement.where(audit_events.c.ator_id == actor_id)
        statement = statement.order_by(audit_events.c.ocorreu_em.desc(), audit_events.c.id.desc()).limit(limit)
        with self._transaction.session() as session:
            return tuple(
                AdminAuditEvent(
                    row.id, str(row.instituicao_id), str(row.ator_id), row.ator_nome,
                    AdminAuditAction(row.acao), row.recurso_tipo, row.recurso_id, row.ocorreu_em,
                )
                for row in session.execute(statement)
            )
