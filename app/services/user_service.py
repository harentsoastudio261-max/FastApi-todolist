"""User service — authentication and user management business logic."""
from app.core.exceptions import ConflictException, UnauthorizedException
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.entities import User
from app.repositories import UserRepository
from app.schemas import UserCreate, UserRead, user_to_read

logger = get_logger(__name__)


class UserService:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def register(self, data: UserCreate) -> UserRead:
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

    def authenticate(self, email: str, password: str) -> str:
        user = self.repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Incorrect email or password", "bad_credentials")
        token = create_access_token(subject=user.id, extra={"email": user.email})
        logger.info("Issued token for user id=%s", user.id)
        return token
