from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RoomPosition:
    space_id: str
    x: float
    y: float

    def __post_init__(self) -> None:
        if not self.space_id.strip():
            raise ValueError("A posição precisa estar vinculada a uma sala.")
        if not (0 <= self.x <= 100 and 0 <= self.y <= 100):
            raise ValueError("As coordenadas devem estar entre 0 e 100.")


@dataclass(frozen=True, slots=True)
class FloorPlan:
    id: str
    institution_id: str
    building_id: str
    floor_id: str
    original_filename: str
    media_type: str
    checksum: str
    storage_key: str
    positions: tuple[RoomPosition, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not all((self.id.strip(), self.institution_id.strip(), self.building_id.strip(), self.floor_id.strip(), self.storage_key.strip())):
            raise ValueError("A planta precisa estar vinculada a uma instituição, prédio e andar.")
        if len({position.space_id for position in self.positions}) != len(self.positions):
            raise ValueError("Uma sala só pode ter uma posição por planta.")

