"""Task service - task business logic (CRUD, ownership rules)."""
from app.core.logging import get_logger
from app.models.entities import Task
from app.repositories import TaskRepository
from app.schemas import (
    SummaryTaskCreate,
    SummaryTaskRead,
    TaskCreate,
    TaskRead,
    TaskUpdate,
    apply_task_update,
    summary_task_create_to_model,
    summary_task_to_read,
    task_create_to_model,
    task_to_read,
)

logger = get_logger(__name__)


class TaskService:
    def __init__(self, repo: TaskRepository):
        self.repo = repo

    def list_tasks(self, user_id: int) -> list[TaskRead]:
        tasks = self.repo.list_by_user(user_id)
        return [task_to_read(t) for t in tasks]

    def create_task(self, data: TaskCreate, user_id: int) -> TaskRead:
        task = task_create_to_model(data, user_id)
        task = self.repo.add(task)
        logger.info("Created task id=%s for user id=%s", task.id, user_id)
        return task_to_read(task)

    def create_summary_task(self, data: SummaryTaskCreate) -> SummaryTaskRead:
        summary_task = summary_task_create_to_model(data)
        summary_task = self.repo.add_summary_task(summary_task)
        logger.info("Created summary task id=%s", summary_task.id)
        return summary_task_to_read(summary_task)

    def get_task(self, task_id: int, user_id: int) -> TaskRead:
        task = self.repo.get_owned(task_id, user_id)
        return task_to_read(task)

    def update_task(self, task_id: int, data: TaskUpdate, user_id: int) -> TaskRead:
        task = self.repo.get_owned(task_id, user_id)
        apply_task_update(task, data)
        self.db_flush()
        self.repo_get_fresh(task)
        logger.info("Updated task id=%s", task.id)
        return task_to_read(task)

    def delete_task(self, task_id: int, user_id: int) -> None:
        task = self.repo.get_owned(task_id, user_id)
        self.repo.delete(task)
        logger.info("Deleted task id=%s", task_id)

    # Helpers to keep service decoupled from session internals.
    def db_flush(self) -> None:
        self.repo.db.flush()

    def repo_get_fresh(self, task: Task) -> None:
        self.repo.db.refresh(task)
