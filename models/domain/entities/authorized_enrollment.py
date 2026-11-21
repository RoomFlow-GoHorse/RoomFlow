from dataclasses import dataclass, replace
from enum import Enum
import re


class EnrollmentStatus(str, Enum):
    ACTIVE = "ativo"
    INACTIVE = "inativo"
    USED = "utilizado"


@dataclass(frozen=True, slots=True)
class AuthorizedEnrollment:
    id: str
    institution_id: str
    registration_number: str
    name: str | None = None
    email: str | None = None
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE
    used_by_user_id: str | None = None

    def __post_init__(self) -> None:
        registration_number = self.registration_number.strip()
        if not self.id.strip() or not self.institution_id.strip() or not registration_number:
            raise ValueError("Identificador, instituição e matrícula são obrigatórios.")
        object.__setattr__(self, "registration_number", registration_number)
        if self.name is not None:
            object.__setattr__(self, "name", self.name.strip() or None)
        if self.email is not None:
            object.__setattr__(self, "email", self.email.strip().lower() or None)
        if not isinstance(self.status, EnrollmentStatus):
            object.__setattr__(self, "status", EnrollmentStatus(self.status))

    @property
    def normalized_registration_number(self) -> str:
        return re.sub(r"\s+", "", self.registration_number).casefold()

    @property
    def is_available(self) -> bool:
        return self.status is EnrollmentStatus.ACTIVE and self.used_by_user_id is None

    def deactivate(self) -> "AuthorizedEnrollment":
        if not self.is_available:
            raise ValueError("Somente matrículas disponíveis podem ser desativadas.")
        return replace(self, status=EnrollmentStatus.INACTIVE)

    def consume(self, user_id: str) -> "AuthorizedEnrollment":
        if not self.is_available:
            raise ValueError("Esta matrícula não está disponível.")
        return replace(self, status=EnrollmentStatus.USED, used_by_user_id=user_id)
