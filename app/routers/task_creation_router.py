"""Task creation router - maps protected AI task creation endpoint."""
from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_manager
from app.controllers.task_creation_controller import TaskCreationController
from app.managers import ServiceManager
from app.models.entities import User
from app.schemas import TaskCreationCreate, TaskRead

router = APIRouter(prefix="/task_creation", tags=["task_creation"])


def _controller(
    manager: ServiceManager = Depends(get_manager),
    current_user: User = Depends(get_current_user),
) -> TaskCreationController:
    return TaskCreationController(manager, current_user)


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task_creation(data: TaskCreationCreate, controller: TaskCreationController = Depends(_controller)):
    return controller.create_task(data)