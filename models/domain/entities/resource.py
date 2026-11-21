from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Resource:
    id: str
    institution_id: str
    name: str
    active: bool = True

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.institution_id.strip():
            raise ValueError("O recurso precisa estar vinculado a uma instituição.")
        if not self.name.strip() or len(self.name.strip()) > 100:
            raise ValueError("O nome do recurso deve ter entre 1 e 100 caracteres.")
