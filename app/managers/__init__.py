"""Manager layer — coordinates a DB session, repositories, and services.

Controllers depend only on this, keeping them thin and testable.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories import TaskRepository, UserRepository
from app.services.task_service import TaskService
from app.services.user_service import UserService


@dataclass
class ServiceManager:
    """Holds the per-request service instances sharing one session."""
    user_service: UserService
    task_service: TaskService
    db: Session


def build_manager(db: Session) -> ServiceManager:
    user_repo = UserRepository(db)
    task_repo = TaskRepository(db)
    return ServiceManager(
        user_service=UserService(user_repo),
        task_service=TaskService(task_repo),
        db=db,
    )
