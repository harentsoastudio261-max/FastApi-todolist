"""Auth router — maps HTTP endpoints to the auth controller."""
from fastapi import APIRouter, Depends, status

from app.api.deps import get_manager
from app.controllers.auth_controller import AuthController
from app.managers import ServiceManager
from app.schemas import Token, UserCreate, UserLogin, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, manager: ServiceManager = Depends(get_manager)):
    controller = AuthController(manager)
    user, _ = controller.register(data)
    return user


@router.post("/login", response_model=Token)
def login(data: UserLogin, manager: ServiceManager = Depends(get_manager)):
    controller = AuthController(manager)
    return controller.login(data)
