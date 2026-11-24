from io import BytesIO
from typing import Any
from zipfile import BadZipFile
from xml.etree.ElementTree import ParseError

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException


class OpenpyxlEnrollmentSpreadsheetParser:
    """Reads enrollment rows from the first worksheet without changing storage."""

    _HEADER_ALIASES = {
        "matricula": "registration_number",
        "matrícula": "registration_number",
        "ra": "registration_number",
        "registration_number": "registration_number",
        "nome": "name",
        "name": "name",
        "email": "email",
        "e-mail": "email",
    }

    def parse(self, content: bytes) -> list[dict[str, str | None]]:
        if not content or len(content) > 10 * 1024 * 1024:
            raise ValueError("A planilha está vazia ou excede o limite de 10 MB.")
        workbook = None
        try:
            workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
            worksheet = workbook.active
            rows = worksheet.iter_rows(values_only=True)
            headers = next(rows, None)
            if not headers:
                raise ValueError("A planilha precisa ter uma linha de cabeçalho.")
            normalized_headers = [
                self._HEADER_ALIASES.get(str(value).strip().casefold()) if value is not None else None
                for value in headers
            ]
            if "registration_number" not in normalized_headers:
                raise ValueError("Inclua uma coluna chamada Matrícula ou RA.")
            parsed: list[dict[str, str | None]] = []
            for row in rows:
                if not any(value is not None and str(value).strip() for value in row):
                    continue
                record: dict[str, str | None] = {
                    "registration_number": None,
                    "name": None,
                    "email": None,
                }
                for index, header in enumerate(normalized_headers):
                    if header and index < len(row) and row[index] is not None:
                        record[header] = str(row[index]).strip() or None
                parsed.append(record)
                if len(parsed) > 5000:
                    raise ValueError("A planilha pode conter no máximo 5.000 linhas.")
            return parsed
        except ValueError:
            raise
        except (OSError, KeyError, TypeError, BadZipFile, ParseError, InvalidFileException) as exc:
            raise ValueError("Não foi possível ler o arquivo Excel enviado.") from exc
        finally:
            if workbook is not None:
                workbook.close()
