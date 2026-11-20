from typing import Protocol


class EmailSender(Protocol):
    def send_verification(self, email: str, token: str) -> None: ...
