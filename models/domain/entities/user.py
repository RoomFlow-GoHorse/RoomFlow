from dataclasses import dataclass
from enum import Enum

from models.domain.entities.profile import Profile


class UserStatus(str, Enum):
    ACTIVE = "ativo"
    INACTIVE = "inativo"


@dataclass(frozen=True, slots=True)
class User:
    """Principal with one active institution link for the confirmed admin scope.

    This field does not decide whether other profiles may have memberships in
    multiple institutions; that cardinality remains a persistence decision.
    """

    id: str
    name: str
    email: str
    profile: Profile
    institution_id: str | None
    status: UserStatus = UserStatus.ACTIVE

    def __post_init__(self) -> None:
        if not isinstance(self.profile, Profile):
            object.__setattr__(self, "profile", Profile(self.profile))
        if not isinstance(self.status, UserStatus):
            object.__setattr__(self, "status", UserStatus(self.status))
        if not self.id.strip():
            raise ValueError("O identificador do usuário é obrigatório.")
        if not self.name.strip():
            raise ValueError("O nome do usuário é obrigatório.")
        if self.profile is Profile.ADMIN and not self.institution_id:
            raise ValueError("O perfil admin precisa estar vinculado a uma instituição.")

    @property
    def is_active(self) -> bool:
        return self.status is UserStatus.ACTIVE
