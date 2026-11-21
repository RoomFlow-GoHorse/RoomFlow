from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ReservationPreferences:
    min_advance: int = 1
    min_advance_unit: str = "dias"
    max_advance: int = 60
    max_advance_unit: str = "semanas"
    allowed_start: str = "07:00"
    allowed_end: str = "22:00"
    automatic_approval: str = "disabled"
    justification_required: bool = True

    def __post_init__(self) -> None:
        if self.min_advance < 1 or self.max_advance < 1:
            raise ValueError("As antecedências devem ser de pelo menos uma unidade.")
        if self.min_advance_unit not in {"dias", "horas"}:
            raise ValueError("Unidade de antecedência mínima inválida.")
        if self.max_advance_unit not in {"dias", "semanas"}:
            raise ValueError("Unidade de antecedência máxima inválida.")
        minimum_days = self.min_advance / 24 if self.min_advance_unit == "horas" else self.min_advance
        maximum_days = self.max_advance * 7 if self.max_advance_unit == "semanas" else self.max_advance
        if maximum_days < minimum_days:
            raise ValueError("A antecedência máxima não pode ser menor que a mínima.")
        if self.automatic_approval not in {"disabled", "no_conflict"}:
            raise ValueError("Opção de aprovação automática inválida.")
        start = _minutes(self.allowed_start)
        end = _minutes(self.allowed_end)
        if end <= start:
            raise ValueError("O horário final deve ser posterior ao horário inicial.")


@dataclass(frozen=True, slots=True)
class ConflictPreferences:
    resolution_criterion: str = "manual"
    notification_timing: str = "immediate"
    suggest_alternatives: bool = True

    def __post_init__(self) -> None:
        if self.resolution_criterion not in {"priority", "fifo", "requester_role", "manual"}:
            raise ValueError("Critério de resolução de conflito inválido.")
        if self.notification_timing not in {"immediate", "one_hour", "history_only"}:
            raise ValueError("Opção de notificação de conflito inválida.")


@dataclass(frozen=True, slots=True)
class NotificationPreferences:
    reservation_approved: bool = True
    reservation_rejected: bool = True
    conflict_detected: bool = True
    space_changed: bool = True
    reservation_cancelled: bool = True
    reservation_reminder: bool = True


@dataclass(frozen=True, slots=True)
class InstitutionPreferences:
    reservations: ReservationPreferences = field(default_factory=ReservationPreferences)
    conflicts: ConflictPreferences = field(default_factory=ConflictPreferences)
    notifications: NotificationPreferences = field(default_factory=NotificationPreferences)


def _minutes(value: str) -> int:
    try:
        hour, minute = (int(part) for part in value.split(":"))
    except (ValueError, AttributeError):
        raise ValueError("Informe um horário válido no formato HH:MM.") from None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("Informe um horário válido no formato HH:MM.")
    return hour * 60 + minute


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
    address: str | None = None
    timezone: str = "America/Sao_Paulo"
    preferences: InstitutionPreferences = field(default_factory=InstitutionPreferences)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("O identificador da instituição é obrigatório.")
        if not self.name.strip():
            raise ValueError("O nome da instituição é obrigatório.")
        if self.timezone not in {
            "America/Sao_Paulo", "America/Manaus", "America/Fortaleza"
        }:
            raise ValueError("Fuso horário não suportado.")
