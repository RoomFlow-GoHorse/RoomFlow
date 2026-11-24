from typing import Protocol


class EmailDeliveryUnavailable(Exception):
    pass


class EmailSender(Protocol):
    def send_verification(self, email: str, token: str) -> None: ...

    def send_password_reset(self, email: str, token: str) -> None: ...
