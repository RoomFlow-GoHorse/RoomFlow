from typing import Protocol, Sequence


class EnrollmentSpreadsheetParser(Protocol):
    def parse(self, content: bytes) -> Sequence[dict[str, str | None]]: ...
