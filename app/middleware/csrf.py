"""HTTP-wide CSRF request validation."""
from hmac import compare_digest

from fastapi.requests import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class CsrfMiddleware(BaseHTTPMiddleware):
    """Reject unsafe browser requests unless the cookie and custom header match."""

    def __init__(self, app, *, cookie_name: str, header_name: str) -> None:
        super().__init__(app)
        self.cookie_name = cookie_name
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        if request.method not in UNSAFE_METHODS:
            return await call_next(request)

        cookie_token = request.cookies.get(self.cookie_name)
        header_token = request.headers.get(self.header_name)
        if not cookie_token or not header_token or not compare_digest(cookie_token, header_token):
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "csrf_validation_failed",
                        "message": "Missing or invalid CSRF token",
                    }
                },
            )

        return await call_next(request)
