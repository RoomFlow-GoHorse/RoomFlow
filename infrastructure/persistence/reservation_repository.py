from sqlalchemy import distinct, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased

from application.ports.reservation_dashboard_query import ReservationDashboardMetrics
from infrastructure.persistence.records import reservation_history
from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.user_mapping import to_database_identity_id
from models.database_models import ConflitoReserva, Espaco, Reserva, ReservaParticipante, Usuario
from models.domain.entities.reservation import (
    EDITABLE, Reservation, ReservationDetails, ReservationHistoryAction, ReservationHistoryEvent,
    ReservationParticipant, ReservationPeriod, ReservationRequest, ReservationStatus,
)
from models.domain.exceptions import DuplicateResource, ResourceNotFound
from models.domain.entities.reservation_conflict import ConflictStatus


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

    def list_for_participant(self, institution_id: str, participant_id: str) -> list[ReservationDetails]:
        with self._transaction.session() as session:
            statement = self._listing(institution_id).join(
                ReservaParticipante,
                (ReservaParticipante.reserva_id == Reserva.id)
                & (ReservaParticipante.instituicao_id == Reserva.instituicao_id),
            ).where(ReservaParticipante.usuario_id == to_database_identity_id(participant_id)).order_by(
                Reserva.inicio.desc(), Reserva.id.desc(),
            )
            return [self._details(row) for row in session.execute(statement)]

    def participants(self, institution_id: str, reservation_id: str) -> list[ReservationParticipant]:
        with self._transaction.session() as session:
            rows = session.execute(
                select(ReservaParticipante, Usuario).join(Usuario, Usuario.id == ReservaParticipante.usuario_id).where(
                    ReservaParticipante.instituicao_id == to_database_identity_id(institution_id),
                    ReservaParticipante.reserva_id == to_database_identity_id(reservation_id, bits=64),
                ).order_by(Usuario.name, Usuario.id)
            )
            return [ReservationParticipant(str(link.usuario_id), user.name, user.email, link.status, link.criado_em, link.respondido_em)
                    for link, user in rows]

    def participation_status(self, institution_id: str, reservation_id: str, participant_id: str) -> str | None:
        with self._transaction.session() as session:
            return session.scalar(select(ReservaParticipante.status).where(
                ReservaParticipante.instituicao_id == to_database_identity_id(institution_id),
                ReservaParticipante.reserva_id == to_database_identity_id(reservation_id, bits=64),
                ReservaParticipante.usuario_id == to_database_identity_id(participant_id),
            ))

    def set_participation_status(self, institution_id, reservation_id, participant_id, status, responded_at) -> bool:
        with self._transaction.session() as session:
            result = session.execute(update(ReservaParticipante).where(
                ReservaParticipante.instituicao_id == to_database_identity_id(institution_id),
                ReservaParticipante.reserva_id == to_database_identity_id(reservation_id, bits=64),
                ReservaParticipante.usuario_id == to_database_identity_id(participant_id),
            ).values(status=status, respondido_em=responded_at, atualizado_em=responded_at))
            return result.rowcount == 1

    def replace_participants(self, institution_id: str, reservation_id: str, participant_ids: frozenset[str]) -> None:
        with self._transaction.session() as session:
            reservation = to_database_identity_id(reservation_id, bits=64)
            institution = to_database_identity_id(institution_id)
            session.query(ReservaParticipante).filter(
                ReservaParticipante.instituicao_id == institution, ReservaParticipante.reserva_id == reservation,
            ).delete(synchronize_session=False)
            for participant_id in participant_ids:
                session.add(ReservaParticipante(instituicao_id=institution, reserva_id=reservation,
                                                usuario_id=to_database_identity_id(participant_id)))
            try:
                session.flush()
            except IntegrityError as exc:
                raise DuplicateResource("Os participantes informados não são válidos para esta instituição.") from exc

    def list_for_period(
        self, institution_id: str, period: ReservationPeriod, space_ids: frozenset[str],
    ) -> list[ReservationDetails]:
        if not space_ids:
            return []
        ids = [to_database_identity_id(item, bits=64) for item in space_ids]
        statement = self._listing(institution_id).where(
            Reserva.espaco_id.in_(ids), Reserva.inicio < period.end, Reserva.fim > period.start,
        ).order_by(Reserva.inicio, Reserva.id)
        with self._transaction.session() as session:
            return [self._details(row) for row in session.execute(statement)]

    def get_metrics(
        self, institution_id: str, start_at: datetime, end_at: datetime,
        *, space_ids: frozenset[str] | None = None,
    ) -> ReservationDashboardMetrics:
        if space_ids is not None and not space_ids:
            return ReservationDashboardMetrics(0, 0, 0, 0, 0)
        institution = to_database_identity_id(institution_id)
        approved = Reserva.status == ReservationStatus.APPROVED
        counts = select(
            func.count(),
            func.count().filter(Reserva.status.in_((ReservationStatus.PENDING, ReservationStatus.IN_REVIEW))),
            func.count().filter(approved),
            func.count().filter(Reserva.status == ReservationStatus.REJECTED),
            func.count().filter(Reserva.status == ReservationStatus.CANCELLED),
            func.count(distinct(Reserva.espaco_id)).filter(approved),
        ).where(Reserva.instituicao_id == institution, Reserva.inicio < end_at, Reserva.fim > start_at)
        a, b = aliased(Reserva), aliased(Reserva)
        conflicts = (
            select(func.count()).select_from(ConflitoReserva)
            .join(a, (a.id == ConflitoReserva.reserva_a_id) & (a.instituicao_id == institution))
            .join(b, (b.id == ConflitoReserva.reserva_b_id) & (b.instituicao_id == institution))
            .where(
                ConflitoReserva.instituicao_id == institution, ConflitoReserva.status != ConflictStatus.RESOLVED,
                a.espaco_id == b.espaco_id, a.status.in_(EDITABLE), b.status.in_(EDITABLE),
                func.greatest(a.inicio, b.inicio, start_at) < func.least(a.fim, b.fim, end_at),
            )
        )
        if space_ids is not None:
            ids = [to_database_identity_id(item, bits=64) for item in space_ids]
            counts = counts.where(Reserva.espaco_id.in_(ids))
            conflicts = conflicts.where(a.espaco_id.in_(ids))
        with self._transaction.session() as session:
            total, pending, approved_count, rejected, cancelled, occupied = session.execute(counts).one()
            open_conflicts = session.scalar(conflicts)
        return ReservationDashboardMetrics(
            total, pending, approved_count, open_conflicts, occupied, rejected=rejected, cancelled=cancelled,
        )

    def find_many(self, institution_id: str, reservation_ids: set[str]) -> dict[str, ReservationDetails]:
        if not reservation_ids:
            return {}
        ids = [to_database_identity_id(value, bits=64) for value in reservation_ids]
        with self._transaction.session() as session:
            statement = self._listing(institution_id).where(Reserva.id.in_(ids))
            return {str(row[0].id): self._details(row) for row in session.execute(statement)}

    def find_with_history(
        self, institution_id: str, reservation_id: str, requester_id: str | None = None,
    ) -> tuple[ReservationDetails, list[ReservationHistoryEvent]] | None:
        try:
            database_id = to_database_identity_id(reservation_id, bits=64)
        except ValueError:
            return None
        columns = reservation_history.c
        statement = (
            self._listing(institution_id, requester_id)
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
