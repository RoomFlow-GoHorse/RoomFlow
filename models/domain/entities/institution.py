from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Institution:
    id: str
    name: str

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("O identificador da instituição é obrigatório.")
        if not self.name.strip():
            raise ValueError("O nome da instituição é obrigatório.")
