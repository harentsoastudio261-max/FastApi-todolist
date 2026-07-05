"""Use case that orchestrates AI task creation."""
from app.core.exceptions import ValidationException
from app.schemas import TaskCreationCreate, TaskCreationType, TaskRead
from app.services.hobbies_task_creation_service import HobbiesTaskCreationService
from app.services.work_task_creation_service import WorkTaskCreationService


class TaskCreationUseCase:
    def __init__(
        self,
        hobbies_service: HobbiesTaskCreationService,
        work_service: WorkTaskCreationService,
    ):
        self.hobbies_service = hobbies_service
        self.work_service = work_service

    def create_task(self, data: TaskCreationCreate, user_id: int) -> TaskRead:
        if data.type == TaskCreationType.HOBBIES:
            return self.hobbies_service.create(user_id)

        if data.type == TaskCreationType.WORK:
            return self.work_service.create(user_id)

        raise ValidationException("Unsupported task creation type", "unsupported_task_creation_type")