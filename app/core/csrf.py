"""CSRF primitives shared by the HTTP middleware and authentication routes."""
from hmac import compare_digest
from secrets import token_urlsafe

from fastapi import Response
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


# This module centralizes CSRF rules so routers stay limited to HTTP wiring.
def generate_csrf_token() -> str:
    """Return an unpredictable token suitable for the synchronizer-token pattern."""
    return token_urlsafe(32)


# The token is kept in an HttpOnly cookie and returned only to the trusted SPA bootstrap call.
def issue_csrf_token(response: Response) -> str:
    """Rotate the CSRF cookie and return its matching value for the response body."""
    # Load settings only when issuing a browser cookie, keeping middleware tests infrastructure-free.
    from app.core.config import settings

    token = generate_csrf_token()
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=token,
        httponly=True,
        secure=settings.csrf_cookie_secure,
        samesite=settings.csrf_cookie_samesite,
        max_age=settings.csrf_token_expire_seconds,
        path="/",
    )
    return token


# Clear the companion CSRF cookie whenever the authenticated session is closed.
def clear_csrf_cookie(response: Response) -> None:
    """Remove the CSRF cookie from the browser."""
    # Cookie naming remains environment-configurable without coupling request validation to settings.
    from app.core.config import settings

    response.delete_cookie(key=settings.csrf_cookie_name, path="/")


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
