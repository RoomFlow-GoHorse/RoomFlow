from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from infrastructure.persistence.records import reservation_history
from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.user_mapping import to_database_identity_id
from models.database_models import Espaco, Reserva, Usuario
from models.domain.entities.reservation import (
    EDITABLE, Reservation, ReservationDetails, ReservationHistoryAction, ReservationHistoryEvent,
    ReservationPeriod, ReservationRequest, ReservationStatus,
)
from models.domain.exceptions import DuplicateResource, ResourceNotFound


class PostgresReservationRepository:
    def __init__(self, transaction: PostgresTransaction):
        self._transaction = transaction

    def add(self, reservation: Reservation) -> ReservationDetails:
        with self._transaction.session() as session:
            row = Reserva(
                instituicao_id=to_database_identity_id(reservation.institution_id),
                solicitante_id=to_database_identity_id(reservation.requester_id),
                criado_em=reservation.created_at,
            )
            session.add(row)
            return self._write(session, row, reservation)

    def save(self, reservation: Reservation) -> ReservationDetails:
        with self._transaction.session() as session:
            row = session.scalar(select(Reserva).where(
                Reserva.id == to_database_identity_id(reservation.id, bits=64),
                Reserva.instituicao_id == to_database_identity_id(reservation.institution_id),
                Reserva.solicitante_id == to_database_identity_id(reservation.requester_id),
            ))
            if row is None:
                raise ResourceNotFound("Reserva não encontrada.")
            return self._write(session, row, reservation)

    def find(self, institution_id, reservation_id, requester_id=None):
        try:
            database_id = to_database_identity_id(reservation_id, bits=64)
        except ValueError:
            return None
        with self._transaction.session() as session:
            statement = self._listing(institution_id, requester_id).where(Reserva.id == database_id)
            row = session.execute(statement).first()
            return self._details(row) if row is not None else None

    def list(self, institution_id, requester_id=None):
        with self._transaction.session() as session:
            statement = self._listing(institution_id, requester_id).order_by(Reserva.inicio.desc(), Reserva.id.desc())
            return [self._details(row) for row in session.execute(statement)]

    def find_many(self, institution_id: str, reservation_ids: set[str]) -> dict[str, ReservationDetails]:
        if not reservation_ids:
            return {}
        ids = [to_database_identity_id(value, bits=64) for value in reservation_ids]
        with self._transaction.session() as session:
            statement = self._listing(institution_id).where(Reserva.id.in_(ids))
            return {str(row[0].id): self._details(row) for row in session.execute(statement)}

    def find_with_history(
        self, institution_id: str, reservation_id: str,
    ) -> tuple[ReservationDetails, list[ReservationHistoryEvent]] | None:
        try:
            database_id = to_database_identity_id(reservation_id, bits=64)
        except ValueError:
            return None
        columns = reservation_history.c
        statement = (
            self._listing(institution_id)
            .add_columns(*columns)
            .outerjoin(reservation_history, (columns.reserva_id == Reserva.id)
                       & (columns.instituicao_id == Reserva.instituicao_id))
            .where(Reserva.id == database_id)
            .order_by(columns.id)
        )
        with self._transaction.session() as session:
            rows = session.execute(statement).all()
            if not rows:
                return None
            return self._details(rows[0][:4]), [
                self._history_event(row._mapping) for row in rows if row._mapping[columns.id] is not None
            ]

    def append_history(self, reservation: Reservation, event: ReservationHistoryEvent) -> None:
        with self._transaction.session() as session:
            try:
                session.execute(reservation_history.insert().values(
                    instituicao_id=to_database_identity_id(reservation.institution_id),
                    reserva_id=to_database_identity_id(reservation.id, bits=64),
                    acao=event.action.value,
                    status_anterior=event.previous_status.value if event.previous_status else None,
                    status=event.status.value,
                    ocorreu_em=event.occurred_at,
                    ator_id=to_database_identity_id(event.actor_id) if event.actor_id is not None else None,
                    ator_nome=event.actor_name,
                    motivo=event.reason,
                ))
            except IntegrityError as exc:
                raise DuplicateResource("Não foi possível registrar o histórico da reserva.") from exc

    def overlapping_spaces(
        self, institution_id: str, period: ReservationPeriod, *,
        approved_only: bool, space_id: str | None = None, exclude_id: str | None = None,
        requester_id: str | None = None,
    ) -> set[str]:
        statuses = [ReservationStatus.APPROVED] if approved_only else EDITABLE
        statement = select(Reserva.espaco_id).where(
            Reserva.instituicao_id == to_database_identity_id(institution_id),
            Reserva.inicio < period.end, Reserva.fim > period.start, Reserva.status.in_(statuses),
        ).distinct()
        if space_id is not None:
            statement = statement.where(Reserva.espaco_id == to_database_identity_id(space_id, bits=64))
        if exclude_id is not None:
            statement = statement.where(Reserva.id != to_database_identity_id(exclude_id, bits=64))
        if requester_id is not None:
            statement = statement.where(Reserva.solicitante_id == to_database_identity_id(requester_id))
        with self._transaction.session() as session:
            return {str(item) for item in session.scalars(statement)}

    def _write(self, session, row: Reserva, reservation: Reservation) -> ReservationDetails:
        request = reservation.request
        row.espaco_id = to_database_identity_id(request.space_id, bits=64)
        row.titulo = request.title
        row.tipo = request.activity_type
        row.inicio = request.period.start
        row.fim = request.period.end
        row.quantidade_participantes = request.participants
        row.justificativa = request.justification
        row.status = reservation.status.value
        row.avaliado_em = reservation.reviewed_at
        row.avaliado_por = to_database_identity_id(reservation.reviewed_by) if reservation.reviewed_by else None
        row.motivo_decisao = reservation.decision_reason
        try:
            session.flush()
        except IntegrityError as exc:
            sqlstate = getattr(exc.orig, "sqlstate", None)
            if sqlstate == "23P01":
                raise DuplicateResource("Já existe uma reserva aprovada para esta sala no período informado.") from exc
            if sqlstate == "23514":
                raise ValueError("Verifique o período e a capacidade da sala.") from exc
            raise DuplicateResource("Não foi possível gravar a reserva com os vínculos informados.") from exc
        result = session.execute(self._listing(reservation.institution_id).where(Reserva.id == row.id)).one()
        return self._details(result)

    @staticmethod
    def _listing(institution_id, requester_id=None):
        other = aliased(Reserva)
        overlap = select(other.id).where(
            other.instituicao_id == Reserva.instituicao_id,
            other.espaco_id == Reserva.espaco_id,
            other.id != Reserva.id,
            other.status.in_(EDITABLE),
            other.inicio < Reserva.fim,
            other.fim > Reserva.inicio,
        ).correlate(Reserva).exists()
        statement = (
            select(Reserva, Espaco.nome, Usuario.name, (Reserva.status.in_(EDITABLE) & overlap).label("has_overlap"))
            .join(Espaco, (Espaco.id == Reserva.espaco_id) & (Espaco.instituicao_id == Reserva.instituicao_id))
            .join(Usuario, Usuario.id == Reserva.solicitante_id)
            .where(Reserva.instituicao_id == to_database_identity_id(institution_id))
        )
        if requester_id is not None:
            statement = statement.where(Reserva.solicitante_id == to_database_identity_id(requester_id))
        return statement

    @staticmethod
    def _details(result) -> ReservationDetails:
        row, space_name, requester_name, has_overlap = result
        reservation = Reservation(
            id=str(row.id), institution_id=str(row.instituicao_id), requester_id=str(row.solicitante_id),
            request=ReservationRequest(
                str(row.espaco_id), row.titulo, row.tipo, ReservationPeriod(row.inicio, row.fim),
                row.quantidade_participantes, row.justificativa,
            ),
            status=ReservationStatus(row.status), created_at=row.criado_em,
            reviewed_by=str(row.avaliado_por) if row.avaliado_por is not None else None,
            reviewed_at=row.avaliado_em, decision_reason=row.motivo_decisao,
        )
        return ReservationDetails(reservation, space_name, requester_name, has_overlap)

    @staticmethod
    def _history_event(row) -> ReservationHistoryEvent:
        columns = reservation_history.c
        previous_status = row[columns.status_anterior]
        actor_id = row[columns.ator_id]
        return ReservationHistoryEvent(
            action=ReservationHistoryAction(row[columns.acao]),
            previous_status=ReservationStatus(previous_status) if previous_status else None,
            status=ReservationStatus(row[columns.status]),
            occurred_at=row[columns.ocorreu_em],
            actor_id=str(actor_id) if actor_id is not None else None,
            actor_name=row[columns.ator_nome],
            reason=row[columns.motivo],
        )
