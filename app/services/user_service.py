"""User service - authentication and user management business logic."""
from datetime import datetime

from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.logging import get_logger
from app.core.rate_limit import RateLimitScope
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expires_at,
    verify_password,
)
from app.models.entities import RefreshToken, User
from app.repositories import RefreshTokenRepository, UserRepository
from app.schemas import Token, UserCreate, UserRead, user_to_read
from app.services.rate_limit_service import RateLimitService

logger = get_logger(__name__)


class UserService:
    def __init__(
        self,
        repo: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        rate_limiter: RateLimitService,
    ):
        self.repo = repo
        self.refresh_tokens = refresh_tokens
        self.rate_limiter = rate_limiter

    def register(self, data: UserCreate) -> UserRead:
        self.rate_limiter.enforce(RateLimitScope.REGISTER_ACCOUNT, str(data.email))
        if self.repo.get_by_email(data.email):
            raise ConflictException("Email already registered", "email_taken")

        user = User(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
        )
        user = self.repo.add(user)
        logger.info("Registered user id=%s email=%s", user.id, user.email)
        return user_to_read(user)

    def authenticate(self, email: str, password: str) -> Token:
        self.rate_limiter.enforce(RateLimitScope.LOGIN_ACCOUNT, email)
        user = self.repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Incorrect email or password", "bad_credentials")
        logger.info("Issued token pair for user id=%s", user.id)
        return self._issue_token_pair(user)

    def refresh_session(self, refresh_token: str) -> Token:
        token_hash = hash_refresh_token(refresh_token)
        stored = self.refresh_tokens.get_by_hash(token_hash)
        if not stored or stored.revoked_at is not None or stored.expires_at <= datetime.utcnow():
            raise UnauthorizedException("Invalid or expired refresh token", "invalid_refresh_token")

        user = self.repo.get_by_id(stored.user_id)
        if user is None:
            raise UnauthorizedException("User no longer exists", "user_not_found")

        self.rate_limiter.enforce(RateLimitScope.REFRESH_USER, str(user.id))

        new_refresh_token = generate_refresh_token()
        new_refresh_hash = hash_refresh_token(new_refresh_token)
        self.refresh_tokens.revoke(stored, replaced_by_hash=new_refresh_hash)
        self.refresh_tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=new_refresh_hash,
                expires_at=refresh_token_expires_at(),
            )
        )
        access_token = create_access_token(subject=user.id, extra={"email": user.email})
        logger.info("Rotated refresh token for user id=%s", user.id)
        return Token(access_token=access_token, refresh_token=new_refresh_token)

    def logout(self, user_id: int, refresh_token: str | None = None, logout_all: bool = False) -> None:
        if logout_all:
            self.refresh_tokens.revoke_all_for_user(user_id)
            logger.info("Revoked all refresh tokens for user id=%s", user_id)
            return

        if not refresh_token:
            raise UnauthorizedException("Refresh token is required for logout", "refresh_token_required")

        token_hash = hash_refresh_token(refresh_token)
        stored = self.refresh_tokens.get_by_hash(token_hash)
        if not stored or stored.user_id != user_id or stored.revoked_at is not None:
            raise UnauthorizedException("Invalid refresh token", "invalid_refresh_token")
        self.refresh_tokens.revoke(stored)
        logger.info("Revoked refresh token for user id=%s", user_id)

    def _issue_token_pair(self, user: User) -> Token:
        access_token = create_access_token(subject=user.id, extra={"email": user.email})
        refresh_token = generate_refresh_token()
        self.refresh_tokens.add(
            RefreshToken(
                user_id=user.id,
                token_hash=hash_refresh_token(refresh_token),
                expires_at=refresh_token_expires_at(),
            )
        )
        return Token(access_token=access_token, refresh_token=refresh_token)
