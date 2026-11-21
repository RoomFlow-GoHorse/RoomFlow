from dataclasses import dataclass
from datetime import datetime

SPACE_STATUSES = frozenset({"disponivel", "ocupado", "bloqueado", "inativo"})


@dataclass(frozen=True, slots=True)
class Space:
    """Read model for the space fields already represented in the UI mocks."""

    id: str
    name: str
    type: str
    capacity: int
    building: str
    floor: str
    location: str
    status: str
    resources: tuple[str, ...]
    occupancy: int
    institution_id: str = "inst-demo"
    building_id: str = ""
    floor_id: str = ""
    active: bool = True
    resource_ids: tuple[str, ...] = ()
    resource_quantities: tuple[tuple[str, int], ...] = ()
    block_reason: str | None = None
    occupancy_verified: bool = False
    created_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.institution_id.strip():
            raise ValueError("Sala e instituição precisam ter identificadores.")
        if not self.name.strip() or len(self.name.strip()) > 120:
            raise ValueError("O nome da sala deve ter entre 1 e 120 caracteres.")
        if not self.type.strip() or len(self.type.strip()) > 80:
            raise ValueError("O tipo da sala deve ter entre 1 e 80 caracteres.")
        if isinstance(self.capacity, bool) or self.capacity < 1 or self.capacity > 10000:
            raise ValueError("A capacidade deve estar entre 1 e 10000 pessoas.")
        if self.status not in SPACE_STATUSES:
            raise ValueError("Status de sala inválido.")
        if self.status == "inativo" and self.active:
            raise ValueError("Uma sala inativa não pode estar marcada como ativa.")
        if self.occupancy < 0:
            raise ValueError("A ocupação não pode ser negativa.")
        if len(set(self.resource_ids)) != len(self.resource_ids):
            raise ValueError("Uma sala não pode ter o mesmo recurso associado mais de uma vez.")
