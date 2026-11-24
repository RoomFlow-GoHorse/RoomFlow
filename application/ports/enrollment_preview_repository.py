from datetime import datetime
from typing import Protocol

from models.domain.entities.authorized_enrollment import AuthorizedEnrollment


class EnrollmentPreviewRepository(Protocol):
    def save(
        self, preview_id: str, institution_id: str, enrollments: tuple[AuthorizedEnrollment, ...],
        expires_at: datetime,
    ) -> None: ...

    def find(
        self, preview_id: str, institution_id: str, now: datetime,
    ) -> tuple[AuthorizedEnrollment, ...] | None: ...

    def consume(self, preview_id: str, institution_id: str, at: datetime) -> None: ...
