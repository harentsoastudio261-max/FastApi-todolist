"""Task controller — request handling for task CRUD endpoints."""
from fastapi import status

from app.managers import ServiceManager
from app.models.entities import User
from app.schemas import TaskCreate, TaskRead, TaskUpdate


class TaskController:
    def __init__(self, manager: ServiceManager, current_user: User):
        self.manager = manager
        self.current_user = current_user

    def list_tasks(self) -> list[TaskRead]:
        return self.manager.task_service.list_tasks(self.current_user.id)

    def create_task(self, data: TaskCreate) -> tuple[TaskRead, int]:
        task = self.manager.task_service.create_task(data, self.current_user.id)
        return task, status.HTTP_201_CREATED

    def get_task(self, task_id: int) -> TaskRead:
        return self.manager.task_service.get_task(task_id, self.current_user.id)

    def update_task(self, task_id: int, data: TaskUpdate) -> TaskRead:
        return self.manager.task_service.update_task(task_id, data, self.current_user.id)

    def delete_task(self, task_id: int) -> None:
        self.manager.task_service.delete_task(task_id, self.current_user.id)
