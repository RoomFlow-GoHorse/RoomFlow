from dataclasses import dataclass, field

from models.domain.entities.user import User


@dataclass(frozen=True, slots=True)
class UserAccount:
    """Authentication record that keeps the password hash out of User."""

    user: User
    password_hash: str = field(repr=False)
