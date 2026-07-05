"""Auth controller - request handling for register/login endpoints."""
from fastapi import status

from app.managers import ServiceManager
from app.models.entities import User
from app.schemas import LogoutRequest, Token, UserCreate, UserLogin, UserRead


class AuthController:
    def __init__(self, manager: ServiceManager, current_user: User | None = None):
        self.manager = manager
        self.current_user = current_user

    def register(self, data: UserCreate) -> tuple[UserRead, int]:
        user_read = self.manager.user_service.register(data)
        return user_read, status.HTTP_201_CREATED

    def login(self, data: UserLogin) -> Token:
        return self.manager.user_service.authenticate(data.email, data.password)

    def refresh(self, refresh_token: str) -> Token:
        return self.manager.user_service.refresh_session(refresh_token)

    def logout(self, data: LogoutRequest) -> None:
        if self.current_user is None:
            raise RuntimeError("current_user is required for logout")
        self.manager.user_service.logout(
            user_id=self.current_user.id,
            refresh_token=data.refresh_token,
            logout_all=data.logout_all,
        )
