"""Auth router - maps HTTP endpoints to the auth controller and auth cookies."""
from fastapi import APIRouter, Body, Cookie, Depends, Response, status

from app.api.deps import get_current_user, get_manager
from app.controllers.auth_controller import AuthController
from app.core.config import settings
from app.core.csrf import clear_csrf_cookie, issue_csrf_token
from app.core.exceptions import UnauthorizedException
from app.managers import ServiceManager
from app.models.entities import User
from app.schemas import AuthResponse, CsrfTokenResponse, LogoutRequest, Token, UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


def _cookie_options(max_age: int) -> dict:
    return {
        "httponly": True,
        "secure": settings.auth_cookie_secure,
        "samesite": settings.auth_cookie_samesite,
        "max_age": max_age,
        "path": "/",
    }


def _set_auth_cookies(response: Response, tokens: Token) -> None:
    response.set_cookie(
        key=settings.access_token_cookie_name,
        value=tokens.access_token,
        **_cookie_options(settings.jwt_access_token_expire_minutes * 60),
    )
    response.set_cookie(
        key=settings.refresh_token_cookie_name,
        value=tokens.refresh_token,
        **_cookie_options(settings.refresh_token_expire_days * 24 * 60 * 60),
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(key=settings.access_token_cookie_name, path="/")
    response.delete_cookie(key=settings.refresh_token_cookie_name, path="/")


# This safe endpoint lets the trusted SPA obtain a CSRF token before its first write request.
@router.get("/csrf", response_model=CsrfTokenResponse)
def csrf(response: Response) -> CsrfTokenResponse:
    # CSRF bootstrap responses contain a secret and must never be stored by intermediary caches.
    response.headers["Cache-Control"] = "no-store"
    return CsrfTokenResponse(csrf_token=issue_csrf_token(response))


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, manager: ServiceManager = Depends(get_manager)):
    controller = AuthController(manager)
    user, _ = controller.register(data)
    return user


@router.post("/login", response_model=AuthResponse)
def login(
    data: UserLogin,
    response: Response,
    manager: ServiceManager = Depends(get_manager),
):
    controller = AuthController(manager)
    tokens = controller.login(data)
    _set_auth_cookies(response, tokens)
    # Rotate CSRF after authentication so the token is fresh at a privilege boundary.
    response.headers["Cache-Control"] = "no-store"
    return AuthResponse(message="Logged in", csrf_token=issue_csrf_token(response))


@router.post("/refresh", response_model=AuthResponse)
def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=settings.refresh_token_cookie_name),
    manager: ServiceManager = Depends(get_manager),
):
    if not refresh_token:
        raise UnauthorizedException("Missing refresh token cookie", "missing_refresh_cookie")

    controller = AuthController(manager)
    tokens = controller.refresh(refresh_token)
    _set_auth_cookies(response, tokens)
    # Refresh rotates CSRF together with session cookies to keep the pair synchronized.
    response.headers["Cache-Control"] = "no-store"
    return AuthResponse(message="Session refreshed", csrf_token=issue_csrf_token(response))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    data: LogoutRequest = Body(default_factory=LogoutRequest),
    refresh_token: str | None = Cookie(default=None, alias=settings.refresh_token_cookie_name),
    manager: ServiceManager = Depends(get_manager),
    current_user: User = Depends(get_current_user),
):
    controller = AuthController(manager, current_user)
    controller.logout(
        LogoutRequest(
            refresh_token=None if data.logout_all else refresh_token,
            logout_all=data.logout_all,
        )
    )
    _clear_auth_cookies(response)
    # Logout removes the CSRF cookie too, preventing reuse after the session is closed.
    clear_csrf_cookie(response)
    return None
