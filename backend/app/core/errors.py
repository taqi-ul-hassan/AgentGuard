"""Application exceptions and FastAPI exception handlers."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.schemas import ErrorDetail, ErrorResponse
from app.core.logging import get_logger


logger = get_logger(__name__)

ERROR_STATUS_CODES = {
    "AUDIT_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "INVALID_REQUEST": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "POLICY_LOAD_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "DATABASE_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
    "AUDIT_WRITE_FAILED": status.HTTP_503_SERVICE_UNAVAILABLE,
    "FIREWORKS_API_KEY_MISSING": status.HTTP_503_SERVICE_UNAVAILABLE,
    "FIREWORKS_API_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
    "FIREWORKS_MALFORMED_RESPONSE": status.HTTP_502_BAD_GATEWAY,
    "MALFORMED_VERIFIER_JSON": status.HTTP_502_BAD_GATEWAY,
    "INVALID_VERIFIER_JSON": status.HTTP_502_BAD_GATEWAY,
    "LOCAL_ROCM_API_ERROR": status.HTTP_503_SERVICE_UNAVAILABLE,
    "LOCAL_ROCM_MALFORMED_RESPONSE": status.HTTP_502_BAD_GATEWAY,
}


class AgentGuardError(Exception):
    """Base exception for expected Agent Guard failures."""

    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def _error_payload(code: str, message: str, details: dict | None, request_id: str | None) -> dict:
    response = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            details=details or {},
            request_id=request_id,
        )
    )
    return response.model_dump(mode="json")


def _sanitize_validation_errors(exc: RequestValidationError) -> list[dict]:
    """Return validation errors without echoing submitted clinical content."""
    sanitized_errors: list[dict] = []
    for error in exc.errors():
        sanitized_errors.append(
            {
                "type": error.get("type"),
                "loc": error.get("loc"),
                "msg": error.get("msg"),
            }
        )
    return sanitized_errors


def register_exception_handlers(app: FastAPI) -> None:
    """Register standardized exception handlers."""

    @app.exception_handler(AgentGuardError)
    async def handle_agent_guard_error(request: Request, exc: AgentGuardError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.warning("agent_guard_error", extra={"code": exc.code, "request_id": request_id})
        return JSONResponse(
            status_code=ERROR_STATUS_CODES.get(exc.code, status.HTTP_400_BAD_REQUEST),
            content=_error_payload(exc.code, exc.message, exc.details, request_id),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.warning("validation_error", extra={"request_id": request_id})
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_payload(
                "INVALID_REQUEST",
                "Request validation failed.",
                {"errors": _sanitize_validation_errors(exc)},
                request_id,
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception("internal_error", extra={"request_id": request_id})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_payload("INTERNAL_ERROR", "An unexpected error occurred.", {}, request_id),
        )
