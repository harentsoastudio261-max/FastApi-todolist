"""Auth controller — request handling for register/login endpoints."""
from fastapi import status

from app.managers import ServiceManager
from app.schemas import Token, UserCreate, UserLogin, UserRead


class AuthController:
    def __init__(self, manager: ServiceManager):
        self.manager = manager

    def register(self, data: UserCreate) -> tuple[UserRead, int]:
        user_read = self.manager.user_service.register(data)
        return user_read, status.HTTP_201_CREATED

    def login(self, data: UserLogin) -> Token:
        token = self.manager.user_service.authenticate(data.email, data.password)
        return Token(access_token=token)
