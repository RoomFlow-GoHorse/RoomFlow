
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReservationType:
    id: str
    institution_id: str
    name: str
    description: str = ""
    active: bool = True

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.institution_id.strip():
            raise ValueError("O tipo de reserva precisa estar vinculado a uma instituição.")

        if not self.name.strip() or len(self.name.strip()) > 100:
            raise ValueError("O nome deve ter entre 1 e 100 caracteres.")

        if len(self.description) > 255:
            raise ValueError("A descrição deve ter no máximo 255 caracteres.")
