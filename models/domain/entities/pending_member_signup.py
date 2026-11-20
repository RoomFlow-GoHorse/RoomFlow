from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PendingMemberSignup:
    token_digest: str
    institution_id: str
    registration_number: str
    name: str
    email: str
    password_hash: str = field(repr=False)
    invitation_digest: str
    expires_at: datetime
