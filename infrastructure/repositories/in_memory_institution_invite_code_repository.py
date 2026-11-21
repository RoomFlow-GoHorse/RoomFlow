from datetime import datetime
from threading import RLock

from infrastructure.in_memory_admin_transaction import InMemoryAdminTransaction
from models.domain.entities.institution_invite_code import InstitutionInviteCode


class InMemoryInstitutionInviteCodeRepository:
    """Stores only the current digest per institution; raw codes are never persisted."""

    def __init__(self, *, transaction: InMemoryAdminTransaction | None = None) -> None:
        self._lock = transaction.lock if transaction is not None else RLock()
        self._active_digest_by_institution: dict[str, str] = {}
        self._records_by_digest: dict[str, InstitutionInviteCode] = {}
        if transaction is not None:
            transaction.register(self._active_digest_by_institution, self._records_by_digest)

    def find_active(self, institution_id: str) -> InstitutionInviteCode | None:
        with self._lock:
            digest = self._active_digest_by_institution.get(institution_id)
            code = self._records_by_digest.get(digest) if digest else None
            return code if code and code.is_active else None

    def find_active_by_digest(self, digest: str) -> InstitutionInviteCode | None:
        with self._lock:
            return next(
                (code for code in self._records_by_digest.values()
                 if code.is_active and code.digest == digest),
                None,
            )

    def replace(self, code: InstitutionInviteCode) -> None:
        with self._lock:
            existing_digest = self._active_digest_by_institution.get(code.institution_id)
            existing = self._records_by_digest.get(existing_digest) if existing_digest else None
            if code.digest in self._records_by_digest:
                raise ValueError("O código gerado já foi utilizado; gere outro.")
            if existing:
                self._records_by_digest[existing.digest] = existing.revoke(code.created_at)
            self._records_by_digest[code.digest] = code
            self._active_digest_by_institution[code.institution_id] = code.digest

    def revoke(self, institution_id: str, at: datetime) -> InstitutionInviteCode | None:
        with self._lock:
            digest = self._active_digest_by_institution.pop(institution_id, None)
            existing = self._records_by_digest.get(digest) if digest else None
            if existing is None or not existing.is_active:
                return None
            revoked = existing.revoke(at)
            self._records_by_digest[existing.digest] = revoked
            return revoked
