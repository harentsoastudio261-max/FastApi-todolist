"""FastAPI dependencies: current user extraction from Bearer token."""
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.security import decode_access_token
from app.managers import ServiceManager, build_manager
from app.models.entities import User


def get_manager(db: Session = Depends(get_db)) -> ServiceManager:
    return build_manager(db)


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedException("Missing or invalid Authorization header", "missing_bearer")
    return authorization.split(" ", 1)[1].strip()


def get_current_user(
    authorization: str | None = Header(default=None),
    manager: ServiceManager = Depends(get_manager),
) -> User:
    token = _extract_token(authorization)
    payload = decode_access_token(token)
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise UnauthorizedException("Invalid token payload", "invalid_token")

    user = manager.user_service.repo.get_by_id(user_id)
    if user is None:
        raise UnauthorizedException("User no longer exists", "user_not_found")
    return user
