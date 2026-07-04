"""Global exception handlers translating app exceptions to JSON responses."""
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions import AppException, DatabaseException
from app.core.logging import get_logger

logger = get_logger(__name__)


def _error_response(status_code: int, detail: str, error_code: str, extra: dict | None = None) -> JSONResponse:
    payload = {"error": {"code": error_code, "message": detail}}
    if extra:
        payload["error"]["details"] = extra
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.warning("AppException %s on %s %s: %s", exc.error_code, request.method, request.url.path, exc.detail)
        return _error_response(exc.status_code, exc.detail, exc.error_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.info("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Request validation failed",
            "validation_error",
            extra=exc.errors(),
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.exception("Integrity error on %s %s", request.method, request.url.path)
        return _error_response(
            status.HTTP_409_CONFLICT,
            "Data integrity conflict (duplicate or constraint violation)",
            "conflict",
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Database error on %s %s", request.method, request.url.path)
        wrapped = DatabaseException(str(exc))
        return _error_response(wrapped.status_code, wrapped.detail, wrapped.error_code)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error",
            "internal_error",
        )
