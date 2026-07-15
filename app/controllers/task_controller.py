"""Task controller - request handling for task CRUD endpoints."""
from fastapi import status

from app.core.exceptions import UnauthorizedException
from app.managers import ServiceManager
from app.models.entities import User
from app.schemas import SummaryTaskCreate, SummaryTaskRead, TaskCreate, TaskRead, TaskUpdate


class TaskController:
    def __init__(self, manager: ServiceManager, current_user: User | None = None):
        self.manager = manager
        self.current_user = current_user

    def _require_current_user_id(self) -> int:
        if self.current_user is None:
            raise UnauthorizedException("Authentication required", "unauthorized")
        return self.current_user.id

    def list_tasks(self) -> list[TaskRead]:
        return self.manager.task_service.list_tasks(self._require_current_user_id())

    def create_task(self, data: TaskCreate) -> tuple[TaskRead, int]:
        task = self.manager.task_service.create_task(data, self._require_current_user_id())
        return task, status.HTTP_201_CREATED

    def create_summary_task(self, data: SummaryTaskCreate) -> SummaryTaskRead:
        return self.manager.task_service.create_summary_task(data, self._require_current_user_id())

    def get_task(self, task_id: int) -> TaskRead:
        return self.manager.task_service.get_task(task_id, self._require_current_user_id())

    def update_task(self, task_id: int, data: TaskUpdate) -> TaskRead:
        return self.manager.task_service.update_task(task_id, data, self._require_current_user_id())

    def delete_task(self, task_id: int) -> None:
        self.manager.task_service.delete_task(task_id, self._require_current_user_id())
