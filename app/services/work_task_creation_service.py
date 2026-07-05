"""Work task creation business service."""
from datetime import datetime

from app.core.logging import get_logger
from app.models.entities import Task
from app.models.enums import Priority
from app.providers.ai.base import TaskIdeaProvider
from app.repositories import TaskRepository
from app.schemas import TaskCreationType, TaskRead, task_to_read

logger = get_logger(__name__)


class WorkTaskCreationService:
    def __init__(self, repo: TaskRepository, ai_provider: TaskIdeaProvider):
        self.repo = repo
        self.ai_provider = ai_provider

    def create(self, user_id: int) -> TaskRead:
        idea = self.ai_provider.generate_task_idea(TaskCreationType.WORK)
        current_date = datetime.utcnow()
        task = Task(
            user_id=user_id,
            name=idea.name,
            description=idea.description,
            start_date=current_date,
            end_date=current_date,
            priority=Priority.MEDIUM,
        )
        task = self.repo.add(task)
        logger.info("Created AI work task id=%s for user id=%s", task.id, user_id)
        return task_to_read(task)