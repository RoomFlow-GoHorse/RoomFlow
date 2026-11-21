from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        },
        headers=headers,
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    del request
    code = {
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        429: "too_many_requests",
    }.get(exc.status_code, "http_error")
    message = (
        exc.detail
        if isinstance(exc.detail, str)
        else "A solicitação não pode ser concluída."
    )
    return _error_response(exc.status_code, code, message, headers=exc.headers)


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    del request
    details = [
        {
            "location": [str(part) for part in error.get("loc", ())],
            "message": error.get("msg", "Valor inválido."),
            "type": error.get("type", "value_error"),
        }
        for error in exc.errors()
    ]
    return _error_response(
        422,
        "validation_error",
        "Os dados enviados são inválidos.",
        details,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    del request, exc
    return _error_response(
        500,
        "internal_error",
        "Ocorreu um erro interno.",
    )
