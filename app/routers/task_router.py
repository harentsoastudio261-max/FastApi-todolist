"""Task router - maps HTTP endpoints to the task controller."""
from fastapi import APIRouter, Depends, status

from app.api.deps import get_current_user, get_manager
from app.controllers.task_controller import TaskController
from app.managers import ServiceManager
from app.models.entities import User
from app.schemas import SummaryTaskCreate, SummaryTaskRead, TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _controller(manager: ServiceManager = Depends(get_manager), current_user: User = Depends(get_current_user)) -> TaskController:
    return TaskController(manager, current_user)


def _summary_controller(manager: ServiceManager = Depends(get_manager)) -> TaskController:
    return TaskController(manager)


@router.get("", response_model=list[TaskRead])
def list_tasks(controller: TaskController = Depends(_controller)):
    return controller.list_tasks()


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, controller: TaskController = Depends(_controller)):
    task, _ = controller.create_task(data)
    return task


@router.post("/summary", response_model=SummaryTaskRead, status_code=status.HTTP_201_CREATED)
def create_summary_task(data: SummaryTaskCreate, controller: TaskController = Depends(_summary_controller)):
    return controller.create_summary_task(data)


@router.get("/{task_id}", response_model=TaskRead)
def get_task(task_id: int, controller: TaskController = Depends(_controller)):
    return controller.get_task(task_id)


@router.put("/{task_id}", response_model=TaskRead)
def update_task(task_id: int, data: TaskUpdate, controller: TaskController = Depends(_controller)):
    return controller.update_task(task_id, data)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, controller: TaskController = Depends(_controller)):
    controller.delete_task(task_id)
    return None
