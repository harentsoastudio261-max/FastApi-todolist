"""Task creation controller - protected endpoint handling for AI-created tasks."""
from app.core.exceptions import UnauthorizedException
from app.managers import ServiceManager
from app.models.entities import User
from app.schemas import TaskCreationCreate, TaskRead


class TaskCreationController:
    def __init__(self, manager: ServiceManager, current_user: User | None = None):
        self.manager = manager
        self.current_user = current_user

    def _require_current_user_id(self) -> int:
        if self.current_user is None:
            raise UnauthorizedException("Authentication required", "unauthorized")
        return self.current_user.id

    def create_task(self, data: TaskCreationCreate) -> TaskRead:
        return self.manager.task_creation_use_case.create_task(
            data,
            self._require_current_user_id(),
        )