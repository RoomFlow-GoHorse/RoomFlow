from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Institution:
    id: str
    name: str
    cnpj: str | None = None
    institution_type: str | None = None
    city: str | None = None
    state: str | None = None
    phone: str | None = None
    email: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("O identificador da instituição é obrigatório.")
        if not self.name.strip():
            raise ValueError("O nome da instituição é obrigatório.")
