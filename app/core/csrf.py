"""CSRF token and cookie helpers shared by authentication routes."""
from secrets import token_urlsafe

from fastapi import Response


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
