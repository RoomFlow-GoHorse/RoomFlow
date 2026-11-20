from typing import Protocol

from models.domain.entities.institution_invite_code import InstitutionInviteCode


class InstitutionInviteCodeRepository(Protocol):
    def find_active(self, institution_id: str) -> InstitutionInviteCode | None: ...

    def find_active_by_digest(self, digest: str) -> InstitutionInviteCode | None: ...

    def replace(self, code: InstitutionInviteCode) -> None: ...
