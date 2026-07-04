"""Repository layer — pure data access. No business logic, no HTTP awareness."""
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.entities import Task, User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user


class TaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_user(self, user_id: int) -> list[Task]:
        stmt = select(Task).where(Task.user_id == user_id).order_by(Task.created_at.desc())
        return list(self.db.execute(stmt).scalars().all())

    def get_by_id(self, task_id: int) -> Task | None:
        return self.db.get(Task, task_id)

    def get_owned(self, task_id: int, user_id: int) -> Task:
        """Return a task owned by user_id, or raise NotFoundException."""
        task = self.get_by_id(task_id)
        if task is None or task.user_id != user_id:
            raise NotFoundException("Task not found", "task_not_found")
        return task

    def add(self, task: Task) -> Task:
        self.db.add(task)
        self.db.flush()
        self.db.refresh(task)
        return task

    def delete(self, task: Task) -> None:
        self.db.delete(task)
        self.db.flush()


# Protocol so services can depend on an abstraction, not a concrete class.
class IUserRepository(Protocol):
    def get_by_id(self, user_id: int) -> User | None: ...
    def get_by_email(self, email: str) -> User | None: ...
    def add(self, user: User) -> User: ...


class ITaskRepository(Protocol):
    def list_by_user(self, user_id: int) -> list[Task]: ...
    def get_owned(self, task_id: int, user_id: int) -> Task: ...
    def add(self, task: Task) -> Task: ...
    def delete(self, task: Task) -> None: ...
