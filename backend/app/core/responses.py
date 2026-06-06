from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


def success_response(message: str, data: Any = None) -> dict[str, Any]:
    return {"success": True, "message": message, "data": data if data is not None else {}}


def error_response(message: str, errors: list[Any] | None = None, status_code: int = 400) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "message": message, "errors": errors or []},
    )


async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
    errors = [] if isinstance(exc.detail, str) else [exc.detail]
    return error_response(detail, errors=errors, status_code=exc.status_code)


async def validation_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    errors = exc.errors() if hasattr(exc, "errors") else [str(exc)]
    return error_response("Validation failed", errors=errors, status_code=422)

