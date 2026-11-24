from datetime import datetime

from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError

from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.user_mapping import to_database_identity_id
from models.database_models import DestinatarioNotificacao, Notificacao
from models.domain.entities.notification import Notification
from models.domain.exceptions import DuplicateResource


class PostgresNotificationRepository:
    def __init__(self, transaction: PostgresTransaction) -> None:
        self._transaction = transaction

    def add(self, institution_id: str, item: Notification, recipient_ids: frozenset[str]) -> None:
        institution = to_database_identity_id(institution_id)
        with self._transaction.session() as session:
            try:
                notification_id = session.scalar(insert(Notificacao).values(
                    instituicao_id=institution, titulo=item.title, mensagem=item.message,
                    categoria=item.category, criado_em=item.created_at,
                    reserva_id=to_database_identity_id(item.reservation_id, bits=64) if item.reservation_id else None,
                    conflito_id=to_database_identity_id(item.conflict_id, bits=64) if item.conflict_id else None,
                ).returning(Notificacao.id))
                session.execute(insert(DestinatarioNotificacao), [
                    {"instituicao_id": institution, "notificacao_id": notification_id,
                     "usuario_id": to_database_identity_id(user_id)}
                    for user_id in sorted(recipient_ids)
                ])
            except IntegrityError as exc:
                raise DuplicateResource("Não foi possível registrar a notificação e seus destinatários.") from exc

    @staticmethod
    def _recipient_scope(institution_id: str, user_id: str):
        return (
            DestinatarioNotificacao.instituicao_id == to_database_identity_id(institution_id),
            DestinatarioNotificacao.usuario_id == to_database_identity_id(user_id),
        )

    def inbox(
        self, institution_id: str, user_id: str, *, unread_only: bool,
        category: str | None, limit: int, offset: int,
    ) -> tuple[list[Notification], int]:
        statement = (
            select(Notificacao, DestinatarioNotificacao.lida_em)
            .join(DestinatarioNotificacao, (DestinatarioNotificacao.notificacao_id == Notificacao.id)
                  & (DestinatarioNotificacao.instituicao_id == Notificacao.instituicao_id))
            .where(*self._recipient_scope(institution_id, user_id))
        )
        if unread_only:
            statement = statement.where(DestinatarioNotificacao.lida_em.is_(None))
        if category is not None:
            statement = statement.where(Notificacao.categoria == category)
        with self._transaction.session() as session:
            total = session.scalar(select(func.count()).select_from(statement.subquery()))
            rows = session.execute(statement.order_by(Notificacao.criado_em.desc(), Notificacao.id.desc())
                                   .limit(limit).offset(offset))
            return [self._map(row, read_at) for row, read_at in rows], total

    def unread_count(self, institution_id: str, user_id: str) -> int:
        with self._transaction.session() as session:
            return session.scalar(select(func.count()).select_from(DestinatarioNotificacao).where(
                *self._recipient_scope(institution_id, user_id), DestinatarioNotificacao.lida_em.is_(None),
            ))

    def mark_read(
        self, institution_id: str, user_id: str, notification_id: str, now: datetime,
    ) -> datetime | None:
        try:
            item = to_database_identity_id(notification_id, bits=64)
        except ValueError:
            return None
        statement = (
            update(DestinatarioNotificacao)
            .where(*self._recipient_scope(institution_id, user_id), DestinatarioNotificacao.notificacao_id == item)
            .values(lida_em=func.coalesce(DestinatarioNotificacao.lida_em, now))
            .returning(DestinatarioNotificacao.lida_em)
        )
        with self._transaction.session() as session:
            return session.scalar(statement)

    def mark_all_read(self, institution_id: str, user_id: str, now: datetime) -> int:
        updated = (
            update(DestinatarioNotificacao)
            .where(*self._recipient_scope(institution_id, user_id), DestinatarioNotificacao.lida_em.is_(None))
            .values(lida_em=now).returning(DestinatarioNotificacao.notificacao_id).cte()
        )
        with self._transaction.session() as session:
            return session.scalar(select(func.count()).select_from(updated))

    @staticmethod
    def _map(row: Notificacao, read_at: datetime | None) -> Notification:
        return Notification(
            id=str(row.id), title=row.titulo, message=row.mensagem, category=row.categoria,
            created_at=row.criado_em, read_at=read_at,
            reservation_id=str(row.reserva_id) if row.reserva_id is not None else None,
            conflict_id=str(row.conflito_id) if row.conflito_id is not None else None,
        )
