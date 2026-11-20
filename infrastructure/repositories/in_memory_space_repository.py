from collections.abc import Sequence

from domain.entities.space import Space


class InMemorySpaceRepository:
    """Temporary demo storage; contents reset whenever the API process restarts."""

    def __init__(self, spaces: Sequence[Space] | None = None) -> None:
        self._spaces = tuple(spaces) if spaces is not None else self._demo_spaces()

    def list_all(self) -> tuple[Space, ...]:
        return self._spaces

    @staticmethod
    def _demo_spaces() -> tuple[Space, ...]:
        return (
            Space(
                "s1", "Sala 101", "Sala de aula", 20, "Bloco A", "1º andar",
                "Bloco A, 1º andar", "disponivel", ("Projetor", "Quadro branco"), 64,
            ),
            Space(
                "s2", "Sala 204", "Sala de aula", 30, "Bloco B", "2º andar",
                "Bloco B, 2º andar", "ocupado", ("TV", "Ar-condicionado"), 78,
            ),
            Space(
                "s3", "Auditório Principal", "Auditório", 150, "Bloco A", "Térreo",
                "Bloco A, Térreo", "disponivel", ("Audio", "Microfones", "Projetor"), 52,
            ),
            Space(
                "s4", "Laboratório de Informática", "Laboratório", 40, "Bloco C", "Térreo",
                "Bloco C, Térreo", "disponivel", ("Computadores", "Projetor"), 71,
            ),
            Space(
                "s5", "Auditório A", "Auditório", 80, "Bloco D", "Térreo",
                "Bloco D, Térreo", "bloqueado", ("Áudio",), 12,
            ),
            Space(
                "s6", "Sala de Reuniões B", "Sala de reuniões", 8, "Bloco A", "1º andar",
                "Bloco A, 1º andar", "disponivel", ("Videoconferencia",), 46,
            ),
        )
