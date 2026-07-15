"""Use case that orchestrates AI task creation."""
from app.core.exceptions import ValidationException
from app.core.rate_limit import RateLimitScope
from app.schemas import TaskCreationCreate, TaskCreationType, TaskRead
from app.services.hobbies_task_creation_service import HobbiesTaskCreationService
from app.services.rate_limit_service import RateLimitService
from app.services.work_task_creation_service import WorkTaskCreationService


class TaskCreationUseCase:
    def __init__(
        self,
        hobbies_service: HobbiesTaskCreationService,
        work_service: WorkTaskCreationService,
        rate_limiter: RateLimitService,
    ):
        self.hobbies_service = hobbies_service
        self.work_service = work_service
        self.rate_limiter = rate_limiter

    def create_task(self, data: TaskCreationCreate, user_id: int) -> TaskRead:
        self.rate_limiter.enforce(RateLimitScope.AI_USER, str(user_id))
        if data.type == TaskCreationType.HOBBIES:
            return self.hobbies_service.create(user_id)

        if data.type == TaskCreationType.WORK:
            return self.work_service.create(user_id)

        raise ValidationException("Unsupported task creation type", "unsupported_task_creation_type")
