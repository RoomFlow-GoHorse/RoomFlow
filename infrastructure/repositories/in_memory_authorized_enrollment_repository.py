from threading import RLock
from collections.abc import Callable
from typing import TypeVar
from collections.abc import Sequence

from models.domain.entities.authorized_enrollment import AuthorizedEnrollment
from models.domain.exceptions import DuplicateResource, ResourceNotFound

T = TypeVar("T")


class InMemoryAuthorizedEnrollmentRepository:
    """Thread-safe, institution-scoped temporary enrollment store."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._items: dict[tuple[str, str], AuthorizedEnrollment] = {}
        self._by_id: dict[tuple[str, str], tuple[str, str]] = {}

    def add(self, enrollment: AuthorizedEnrollment) -> None:
        self.add_many([enrollment])

    def add_many(self, enrollments: Sequence[AuthorizedEnrollment]) -> None:
        with self._lock:
            incoming_keys: set[tuple[str, str]] = set()
            incoming_ids: set[tuple[str, str]] = set()
            for enrollment in enrollments:
                key = self._key(enrollment.institution_id, enrollment.registration_number)
                scoped_id = (enrollment.institution_id, enrollment.id)
                if key in self._items or key in incoming_keys:
                    raise DuplicateResource("Há matrículas duplicadas na instituição.")
                if scoped_id in self._by_id or scoped_id in incoming_ids:
                    raise DuplicateResource("O identificador da matrícula já está em uso.")
                incoming_keys.add(key)
                incoming_ids.add(scoped_id)
            for enrollment in enrollments:
                key = self._key(enrollment.institution_id, enrollment.registration_number)
                self._items[key] = enrollment
                self._by_id[(enrollment.institution_id, enrollment.id)] = key

    def find(self, institution_id: str, registration_number: str) -> AuthorizedEnrollment | None:
        with self._lock:
            return self._items.get(self._key(institution_id, registration_number))

    def find_by_id(self, institution_id: str, enrollment_id: str) -> AuthorizedEnrollment | None:
        with self._lock:
            key = self._by_id.get((institution_id, enrollment_id))
            return self._items.get(key) if key else None

    def list_for_institution(self, institution_id: str) -> tuple[AuthorizedEnrollment, ...]:
        with self._lock:
            return tuple(
                item for item in self._items.values()
                if item.institution_id == institution_id
            )

    def save(self, enrollment: AuthorizedEnrollment) -> None:
        with self._lock:
            id_key = (enrollment.institution_id, enrollment.id)
            existing_key = self._by_id.get(id_key)
            new_key = self._key(enrollment.institution_id, enrollment.registration_number)
            current_at_key = self._items.get(new_key)
            if current_at_key and current_at_key.id != enrollment.id:
                raise DuplicateResource("Há uma matrícula duplicada na instituição.")
            if existing_key is None:
                raise ResourceNotFound("Matrícula não encontrada.")
            self._items.pop(existing_key, None)
            self._items[new_key] = enrollment
            self._by_id[id_key] = new_key

    def consume(self, institution_id: str, registration_number: str, user_id: str) -> AuthorizedEnrollment:
        """Atomically reserves the enrollment so simultaneous requests cannot reuse it."""
        with self._lock:
            key = self._key(institution_id, registration_number)
            enrollment = self._items.get(key)
            if enrollment is None or not enrollment.is_available:
                raise ResourceNotFound("Matrícula não disponível.")
            consumed = enrollment.consume(user_id)
            self._items[key] = consumed
            return consumed

    def consume_with(
        self, institution_id: str, registration_number: str, user_id: str,
        operation: Callable[[], T],
    ) -> tuple[AuthorizedEnrollment, T]:
        """Run account creation while the enrollment is locked; commit both or neither."""
        with self._lock:
            key = self._key(institution_id, registration_number)
            enrollment = self._items.get(key)
            if enrollment is None or not enrollment.is_available:
                raise ResourceNotFound("Matrícula não disponível.")
            result = operation()
            consumed = enrollment.consume(user_id)
            self._items[key] = consumed
            return consumed, result

    @staticmethod
    def _key(institution_id: str, registration_number: str) -> tuple[str, str]:
        return institution_id, AuthorizedEnrollment(
            id="normalization", institution_id="normalization", registration_number=registration_number
        ).normalized_registration_number
