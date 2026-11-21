from datetime import datetime

from sqlalchemy import and_, func, literal, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.user_mapping import to_database_identity_id
from models.database_models import ConflitoReserva, Reserva, Usuario
from models.domain.entities.reservation import EDITABLE
from models.domain.entities.reservation_conflict import ConflictStatus, ReservationConflict
from models.domain.exceptions import DuplicateResource


class PostgresConflictRepository:
    def __init__(self, transaction: PostgresTransaction):
        self._transaction = transaction

    @staticmethod
    def _listing(institution_id):
        return (
            select(ConflitoReserva, Usuario.name)
            .outerjoin(Usuario, Usuario.id == ConflitoReserva.resolvido_por)
            .where(ConflitoReserva.instituicao_id == to_database_identity_id(institution_id))
        )

    def list(self, institution_id: str, status: ConflictStatus | None = None) -> list[ReservationConflict]:
        statement = self._listing(institution_id).order_by(
            ConflitoReserva.criado_em.desc(), ConflitoReserva.id.desc(),
        )
        if status is not None:
            statement = statement.where(ConflitoReserva.status == status)
        with self._transaction.session() as session:
            return [self._conflict(row, name) for row, name in session.execute(statement)]

    def find(self, institution_id: str, conflict_id: str) -> ReservationConflict | None:
        try:
            database_id = to_database_identity_id(conflict_id, bits=64)
        except ValueError:
            return None
        with self._transaction.session() as session:
            result = session.execute(self._listing(institution_id).where(ConflitoReserva.id == database_id)).first()
            return self._conflict(*result) if result else None

    def synchronize(self, institution_id: str, now: datetime, actor_id: str, reservation_id: str | None = None) -> int:
        conflicts = ConflitoReserva.__table__
        a, b = Reserva.__table__.alias("a").c, Reserva.__table__.alias("b").c
        institution = to_database_identity_id(institution_id)
        pairs = select(
            a.id.label("a_id"), b.id.label("b_id"),
        ).select_from(a.id.table).join(b.id.table, and_(
            a.instituicao_id == b.instituicao_id, a.espaco_id == b.espaco_id, a.id < b.id,
            a.inicio < b.fim, b.inicio < a.fim,
        )).where(
            a.instituicao_id == institution, a.fim > now, b.fim > now,
            a.status.in_(EDITABLE), b.status.in_(EDITABLE),
        )
        open_conflicts = update(conflicts).where(
            conflicts.c.instituicao_id == institution, conflicts.c.status != ConflictStatus.RESOLVED,
        )
        if reservation_id is not None:
            reservation = to_database_identity_id(reservation_id, bits=64)
            pairs = pairs.where(or_(a.id == reservation, b.id == reservation))
            open_conflicts = open_conflicts.where(or_(
                conflicts.c.reserva_a_id == reservation, conflicts.c.reserva_b_id == reservation,
            ))
        pairs = pairs.subquery()
        new_values = dict(
            status=ConflictStatus.OPEN, motivo="Sobreposição de horários na mesma sala.",
            gravidade="media", criado_em=now,
        )
        register = insert(conflicts).from_select(
            ["instituicao_id", "reserva_a_id", "reserva_b_id", *new_values],
            select(literal(institution), pairs.c.a_id, pairs.c.b_id, *(literal(value) for value in new_values.values())),
        ).on_conflict_do_update(
            constraint="uq_conflitos_reservas",
            set_={**new_values, "decisao": None, "resolvido_por": None, "resolvido_em": None},
            where=conflicts.c.status == ConflictStatus.RESOLVED,
        )
        still_overlaps = select(1).where(
            pairs.c.a_id == conflicts.c.reserva_a_id, pairs.c.b_id == conflicts.c.reserva_b_id,
        ).exists()
        close = open_conflicts.where(~still_overlaps).values(
            status=ConflictStatus.RESOLVED, decisao="As reservas deixaram de se sobrepor.",
            resolvido_por=to_database_identity_id(actor_id), resolvido_em=now,
        )
        with self._transaction.session() as session:
            try:
                registered = session.scalar(select(func.count()).select_from(register.returning(conflicts.c.id).cte()))
                closed = session.scalar(select(func.count()).select_from(close.returning(conflicts.c.id).cte()))
                return registered + closed
            except IntegrityError as exc:
                raise DuplicateResource("Não foi possível atualizar os conflitos das reservas.") from exc

    def resolve(self, conflict: ReservationConflict, decision: str, actor_id: str, now: datetime) -> None:
        statement = update(ConflitoReserva).where(
            ConflitoReserva.id == to_database_identity_id(conflict.id, bits=64),
            ConflitoReserva.instituicao_id == to_database_identity_id(conflict.institution_id),
            ConflitoReserva.status != ConflictStatus.RESOLVED,
        ).values(
            status=ConflictStatus.RESOLVED, decisao=decision,
            resolvido_por=to_database_identity_id(actor_id), resolvido_em=now,
        )
        with self._transaction.session() as session:
            try:
                if session.execute(statement).rowcount != 1:
                    raise DuplicateResource("Este conflito já foi resolvido.")
            except IntegrityError as exc:
                raise DuplicateResource("Não foi possível registrar a resolução do conflito.") from exc

    @staticmethod
    def _conflict(row, resolver_name) -> ReservationConflict:
        return ReservationConflict(
            str(row.id), str(row.instituicao_id), str(row.reserva_a_id), str(row.reserva_b_id),
            ConflictStatus(row.status), row.gravidade, row.motivo, row.criado_em, row.decisao,
            row.resolvido_em, str(row.resolvido_por) if row.resolvido_por is not None else None, resolver_name,
        )
