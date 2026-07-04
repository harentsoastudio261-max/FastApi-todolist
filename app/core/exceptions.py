"""Custom application exceptions with HTTP-aware semantics."""
from fastapi import status


class AppException(Exception):
    """Base application exception. Subclasses define their own HTTP status."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "Internal server error"
    error_code: str = "internal_error"

    def __init__(self, detail: str | None = None, error_code: str | None = None):
        if detail:
            self.detail = detail
        if error_code:
            self.error_code = error_code
        super().__init__(self.detail)


class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found"
    error_code = "not_found"


class ConflictException(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Conflict with current state"
    error_code = "conflict"


class UnauthorizedException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Authentication required"
    error_code = "unauthorized"


class ForbiddenException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Not enough permissions"
    error_code = "forbidden"


class ValidationException(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation error"
    error_code = "validation_error"


class DatabaseException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Database error"
    error_code = "database_error"
