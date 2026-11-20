from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Floor:
    id: str
    building_id: str
    name: str
    active: bool = True

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.building_id.strip():
            raise ValueError("Andar e prédio precisam ter identificadores.")
        if not self.name.strip() or len(self.name.strip()) > 120:
            raise ValueError("O nome do andar deve ter entre 1 e 120 caracteres.")


