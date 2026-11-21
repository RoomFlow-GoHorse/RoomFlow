from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True, slots=True)
class SimulatedEmail:
    recipient: str
    verification_token: str


class InMemoryEmailSender:
    """Development adapter that simulates delivery without an HTTP token endpoint."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._messages: dict[str, SimulatedEmail] = {}
        self._recovery_messages: dict[str, SimulatedEmail] = {}

    def send_verification(self, email: str, token: str) -> None:
        with self._lock:
            self._messages[email.strip().lower()] = SimulatedEmail(email, token)

    def latest_for(self, email: str) -> SimulatedEmail | None:
        with self._lock:
            return self._messages.get(email.strip().lower())

    def send_password_reset(self, email: str, token: str) -> None:
        with self._lock:
            self._recovery_messages[email.strip().lower()] = SimulatedEmail(email, token)

    def latest_recovery_for(self, email: str) -> SimulatedEmail | None:
        with self._lock:
            return self._recovery_messages.get(email.strip().lower())
