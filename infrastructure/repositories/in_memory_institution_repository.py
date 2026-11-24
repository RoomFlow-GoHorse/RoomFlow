from threading import RLock
from collections.abc import Iterable

from infrastructure.in_memory_admin_transaction import InMemoryAdminTransaction
from models.domain.entities.institution import Institution
from models.domain.exceptions import DuplicateResource
from models.domain.identity_normalization import normalize_cnpj


class InMemoryInstitutionRepository:
    """Temporary institution store; contents reset when the process stops."""

    def __init__(self, institutions: Iterable[Institution] = (), *, transaction: InMemoryAdminTransaction | None = None) -> None:
        self._lock = transaction.lock if transaction is not None else RLock()
        self._institutions = {item.id: item for item in institutions}
        if transaction is not None:
            transaction.register(self._institutions)

    def find_by_id(self, institution_id: str) -> Institution | None:
        with self._lock:
            return self._institutions.get(institution_id)

    def find_by_cnpj(self, cnpj: str) -> Institution | None:
        normalized = self.normalize_cnpj(cnpj)
        with self._lock:
            return next(
                (item for item in self._institutions.values()
                 if item.cnpj and self.normalize_cnpj(item.cnpj) == normalized),
                None,
            )

    def add(self, institution: Institution) -> Institution:
        with self._lock:
            if institution.id in self._institutions:
                raise DuplicateResource("O identificador da instituição já está em uso.")
            if institution.cnpj and self.find_by_cnpj(institution.cnpj):
                raise DuplicateResource("Já existe uma instituição com este CNPJ.")
            self._institutions[institution.id] = institution
            return institution

    def save(self, institution: Institution) -> None:
        with self._lock:
            if institution.id not in self._institutions:
                raise KeyError(institution.id)
            if institution.cnpj:
                duplicate = self.find_by_cnpj(institution.cnpj)
                if duplicate and duplicate.id != institution.id:
                    raise DuplicateResource("Já existe uma instituição com este CNPJ.")
            self._institutions[institution.id] = institution

    def list_all(self) -> tuple[Institution, ...]:
        with self._lock:
            return tuple(self._institutions.values())

    def remove(self, institution_id: str) -> None:
        with self._lock:
            self._institutions.pop(institution_id, None)

    @staticmethod
    def normalize_cnpj(cnpj: str) -> str:
        return normalize_cnpj(cnpj)
