from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Expected business error with a stable machine-readable code."""

    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


def _error_payload(
    request: Request, code: str, message: str, details: Any = None
) -> dict[str, Any]:
    return {
        "success": False,
        "data": None,
        "error": {"code": code, "message": message, "details": details},
        "request_id": getattr(request.state, "request_id", "unknown"),
    }


def register_exception_handlers(app: FastAPI) -> None:
    """Install consistent handlers for domain, validation and unexpected errors."""

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_payload(request, exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_payload(
                request,
                "VALIDATION_ERROR",
                "Request validation failed",
                exc.errors(),
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request.app.state.logger.exception("Unhandled application error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=_error_payload(request, "INTERNAL_ERROR", "An unexpected error occurred"),
        )
