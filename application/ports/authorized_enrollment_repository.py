from collections.abc import Callable
from typing import Protocol, Sequence, TypeVar

from models.domain.entities.authorized_enrollment import AuthorizedEnrollment

T = TypeVar("T")


class AuthorizedEnrollmentRepository(Protocol):
    def add(self, enrollment: AuthorizedEnrollment) -> None: ...

    def add_many(self, enrollments: Sequence[AuthorizedEnrollment]) -> None: ...

    def find(self, institution_id: str, registration_number: str) -> AuthorizedEnrollment | None: ...

    def find_by_id(self, institution_id: str, enrollment_id: str) -> AuthorizedEnrollment | None: ...

    def list_for_institution(self, institution_id: str) -> Sequence[AuthorizedEnrollment]: ...

    def save(self, enrollment: AuthorizedEnrollment) -> None: ...

    def consume(self, institution_id: str, registration_number: str, user_id: str) -> AuthorizedEnrollment: ...

    def consume_with(
        self, institution_id: str, registration_number: str, user_id: str,
        operation: Callable[[], T],
    ) -> tuple[AuthorizedEnrollment, T]: ...
