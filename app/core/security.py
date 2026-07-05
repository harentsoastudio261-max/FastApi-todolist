"""Security utilities: password hashing and JWT token creation/verification."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.core.exceptions import UnauthorizedException, ValidationException
from app.core.logging import get_logger

logger = get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Hache un mot de passe en clair avant de le stocker.
# On ne stocke jamais le mot de passe brut en base de donnees, seulement sa version hachee.
# Input: `password` (str) mot de passe fourni par l'utilisateur.
# Output: (str) hash bcrypt pret a etre sauvegarde.
def hash_password(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValidationException("Password must be 72 bytes or less for bcrypt", "password_too_long")
    return pwd_context.hash(password)


# Verifie qu'un mot de passe en clair correspond au hash stocke.
# On utilise cette fonction au login pour comparer ce que tape l'utilisateur avec le hash en base.
# Input: `plain` (str) mot de passe saisi a l'instant.
# Input: `hashed` (str) hash recupere depuis la base.
# Output: (bool) True si les deux correspondent, sinon False.
def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str | int, extra: dict[str, Any] | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": str(subject), "exp": expire, "typ": "access"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        logger.info("JWT decode failed: %s", exc)
        raise UnauthorizedException("Invalid or expired token", "invalid_token")
    if payload.get("typ") != "access":
        raise UnauthorizedException("Invalid token type", "invalid_token_type")
    return payload


def generate_refresh_token() -> str:
    return token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expires_at() -> datetime:
    return datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
