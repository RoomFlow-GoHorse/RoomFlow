from sqlalchemy import select, update

from infrastructure.persistence.records import authorized_enrollments
from infrastructure.persistence.transaction import PostgresTransaction
from infrastructure.persistence.user_mapping import to_database_identity_id
from models.database_models import UsuarioInstituicao
from models.domain.entities.authorized_enrollment import AuthorizedEnrollment, normalize_registration_number
from models.domain.exceptions import DuplicateResource, ResourceNotFound


class PostgresAuthorizedEnrollmentRepository:
    def __init__(self, transaction: PostgresTransaction):
        self._transaction = transaction

    @staticmethod
    def _to_entity(row) -> AuthorizedEnrollment | None:
        if row is None:
            return None
        return AuthorizedEnrollment(
            row.id, str(row.instituicao_id), row.matricula, row.nome, row.email, row.status,
            str(row.utilizado_por) if row.utilizado_por is not None else None,
        )

    def add(self, enrollment: AuthorizedEnrollment) -> None:
        self.add_many([enrollment])

    def add_many(self, enrollments) -> None:
        if not enrollments:
            return
        with self._transaction.atomic(), self._transaction.session() as session:
            by_institution: dict[int, set[str]] = {}
            records = []
            for item in enrollments:
                if len(item.registration_number) > 50:
                    raise ValueError("Informe uma matrícula com até 50 caracteres.")
                institution_id = to_database_identity_id(item.institution_id)
                if institution_id not in by_institution:
                    used = session.scalars(select(UsuarioInstituicao.registration_number).where(
                        UsuarioInstituicao.institution_id == institution_id,
                        UsuarioInstituicao.registration_number.is_not(None),
                    ))
                    existing = session.scalars(select(authorized_enrollments.c.matricula_normalizada).where(
                        authorized_enrollments.c.instituicao_id == institution_id,
                    ))
                    by_institution[institution_id] = {normalize_registration_number(number) for number in used} | set(existing)
                normalized = item.normalized_registration_number
                seen = by_institution[institution_id]
                if normalized in seen:
                    raise DuplicateResource("Há matrículas duplicadas na instituição.")
                seen.add(normalized)
                records.append(dict(
                    id=item.id, instituicao_id=institution_id, matricula=item.registration_number,
                    matricula_normalizada=normalized, nome=item.name, email=item.email,
                    status=item.status.value,
                ))
            session.execute(authorized_enrollments.insert(), records)

    def find(self, institution_id, registration_number):
        with self._transaction.session() as session:
            return self._to_entity(session.execute(select(authorized_enrollments).where(
                authorized_enrollments.c.instituicao_id == to_database_identity_id(institution_id),
                authorized_enrollments.c.matricula_normalizada == normalize_registration_number(registration_number),
            )).first())

    def find_by_id(self, institution_id, enrollment_id):
        with self._transaction.session() as session:
            return self._to_entity(session.execute(select(authorized_enrollments).where(
                authorized_enrollments.c.instituicao_id == to_database_identity_id(institution_id),
                authorized_enrollments.c.id == enrollment_id,
            )).first())

    def list_for_institution(self, institution_id):
        with self._transaction.session() as session:
            return tuple(self._to_entity(row) for row in session.execute(select(authorized_enrollments).where(
                authorized_enrollments.c.instituicao_id == to_database_identity_id(institution_id),
            ).order_by(authorized_enrollments.c.matricula_normalizada)))

    def save(self, enrollment):
        with self._transaction.session() as session:
            result = session.execute(update(authorized_enrollments).where(
                authorized_enrollments.c.instituicao_id == to_database_identity_id(enrollment.institution_id),
                authorized_enrollments.c.id == enrollment.id,
            ).values(status=enrollment.status.value, utilizado_por=(
                to_database_identity_id(enrollment.used_by_user_id) if enrollment.used_by_user_id else None
            )))
            if not result.rowcount:
                raise ResourceNotFound("Matrícula não encontrada.")

    def consume(self, institution_id, registration_number, user_id):
        with self._transaction.atomic(), self._transaction.session() as session:
            item = self.find(institution_id, registration_number)
            if item is None or not item.is_available:
                raise ResourceNotFound("Matrícula não disponível.")
            membership = session.execute(select(UsuarioInstituicao).where(
                UsuarioInstituicao.user_id == to_database_identity_id(user_id),
                UsuarioInstituicao.institution_id == to_database_identity_id(institution_id),
            )).scalar_one_or_none()
            if membership is None or membership.registration_number:
                raise ResourceNotFound("Vínculo sem matrícula não encontrado.")
            membership.registration_number = item.registration_number
            consumed = item.consume(user_id)
            self.save(consumed)
            return consumed

    def consume_with(self, institution_id, registration_number, operation):
        with self._transaction.atomic():
            item = self.find(institution_id, registration_number)
            if item is None or not item.is_available:
                raise ResourceNotFound("Matrícula não disponível.")
            user = operation()
            return self.consume(institution_id, registration_number, user.id), user
