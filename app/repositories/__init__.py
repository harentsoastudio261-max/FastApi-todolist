"""Repository layer - pure data access. No business logic, no HTTP awareness."""
from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.entities import RefreshToken, SummaryTask, Task, User
from app.models.enums import Priority, SummaryTaskStatus


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


class RefreshTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return self.db.execute(stmt).scalar_one_or_none()

    def add(self, refresh_token: RefreshToken) -> RefreshToken:
        self.db.add(refresh_token)
        self.db.flush()
        self.db.refresh(refresh_token)
        return refresh_token

    def revoke(self, refresh_token: RefreshToken, replaced_by_hash: str | None = None) -> RefreshToken:
        refresh_token.revoked_at = datetime.utcnow()
        refresh_token.replaced_by_hash = replaced_by_hash
        self.db.flush()
        self.db.refresh(refresh_token)
        return refresh_token

    def revoke_all_for_user(self, user_id: int) -> None:
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        for refresh_token in self.db.execute(stmt).scalars().all():
            refresh_token.revoked_at = datetime.utcnow()
        self.db.flush()


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

    def add_summary_task(self, summary_task: SummaryTask) -> SummaryTask:
        self.db.add(summary_task)
        self.db.flush()
        self.db.refresh(summary_task)
        return summary_task

    def delete(self, task: Task) -> None:
        self.db.delete(task)
        self.db.flush()


#----------------------------------------------
# ajut watcher
#------------------------------------------
class SummaryTaskRepository:
    #----------------------------------------------
    # ajut watcher
    #------------------------------------------
    def __init__(self, db: Session):
        self.db = db
    #----------------------------------------------
    # ajut watcher
    #------------------------------------------

    #----------------------------------------------
    # ajut watcher
    #------------------------------------------
    def list_user_ids(self) -> list[int]:
        stmt = select(User.id).order_by(User.id.asc())
        return list(self.db.execute(stmt).scalars().all())
    #----------------------------------------------
    # ajut watcher
    #------------------------------------------

    #----------------------------------------------
    # ajut watcher
    #------------------------------------------
    def claim_pending(self, limit: int) -> list[SummaryTask]:
        if limit <= 0:
            return []

        now = datetime.utcnow()
        stmt = (
            select(SummaryTask)
            .where(SummaryTask.status == SummaryTaskStatus.PENDING)
            .order_by(SummaryTask.id.asc())
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        summary_tasks = list(self.db.execute(stmt).scalars().all())

        for summary_task in summary_tasks:
            summary_task.status = SummaryTaskStatus.PROCESSING
            summary_task.processing_started_at = now
            summary_task.processed_at = None
            summary_task.processing_error = None

        self.db.flush()
        return summary_tasks
    #----------------------------------------------
    # ajut watcher
    #------------------------------------------

    #----------------------------------------------
    # ajut watcher
    #------------------------------------------
    def mark_processed(self, summary_task_id: int) -> None:
        summary_task = self.db.get(SummaryTask, summary_task_id)
        if summary_task is None:
            return

        summary_task.status = SummaryTaskStatus.PROCESSED
        summary_task.processing_started_at = None
        summary_task.processed_at = datetime.utcnow()
        summary_task.processing_error = None
        self.db.flush()
    #----------------------------------------------
    # ajut watcher
    #------------------------------------------

    #----------------------------------------------
    # ajut watcher
    #------------------------------------------
    def mark_failed(self, summary_task_id: int, reason: str) -> None:
        summary_task = self.db.get(SummaryTask, summary_task_id)
        if summary_task is None:
            return

        summary_task.status = SummaryTaskStatus.FAILED
        summary_task.processing_started_at = None
        summary_task.processed_at = datetime.utcnow()
        summary_task.processing_error = reason[:1000]
        self.db.flush()
    #----------------------------------------------
    # ajut watcher
    #------------------------------------------

    #----------------------------------------------
    # ajut watcher
    #------------------------------------------
    def reset_stale_processing(self, before: datetime) -> int:
        stmt = select(SummaryTask).where(
            SummaryTask.status == SummaryTaskStatus.PROCESSING,
            SummaryTask.processing_started_at.is_not(None),
            SummaryTask.processing_started_at < before,
        )
        stale_summary_tasks = list(self.db.execute(stmt).scalars().all())

        for summary_task in stale_summary_tasks:
            summary_task.status = SummaryTaskStatus.PENDING
            summary_task.processing_started_at = None
            summary_task.processing_error = None

        self.db.flush()
        return len(stale_summary_tasks)
    #----------------------------------------------
    # ajut watcher
    #------------------------------------------

    #----------------------------------------------
    # ajut watcher
    #------------------------------------------
    def create_tasks_for_users(
        self,
        *,
        summary_task_id: int,
        user_ids: list[int],
        name: str,
        description: str,
        current_date: datetime,
    ) -> int:
        if not user_ids:
            return 0

        existing_stmt = select(Task.user_id).where(
            Task.source_summary_task_id == summary_task_id,
            Task.user_id.in_(user_ids),
        )
        existing_user_ids = set(self.db.execute(existing_stmt).scalars().all())

        tasks = [
            Task(
                user_id=user_id,
                name=name,
                description=description,
                start_date=current_date,
                end_date=current_date,
                priority=Priority.MEDIUM,
                source_summary_task_id=summary_task_id,
            )
            for user_id in user_ids
            if user_id not in existing_user_ids
        ]

        if not tasks:
            return 0

        self.db.add_all(tasks)
        self.db.flush()
        return len(tasks)
    #----------------------------------------------
    # ajut watcher
    #------------------------------------------
#----------------------------------------------
# ajut watcher
#------------------------------------------


# Protocol so services can depend on an abstraction, not a concrete class.
class IUserRepository(Protocol):
    def get_by_id(self, user_id: int) -> User | None: ...
    def get_by_email(self, email: str) -> User | None: ...
    def add(self, user: User) -> User: ...


class IRefreshTokenRepository(Protocol):
    def get_by_hash(self, token_hash: str) -> RefreshToken | None: ...
    def add(self, refresh_token: RefreshToken) -> RefreshToken: ...
    def revoke(self, refresh_token: RefreshToken, replaced_by_hash: str | None = None) -> RefreshToken: ...
    def revoke_all_for_user(self, user_id: int) -> None: ...


class ITaskRepository(Protocol):
    def list_by_user(self, user_id: int) -> list[Task]: ...
    def get_owned(self, task_id: int, user_id: int) -> Task: ...
    def add(self, task: Task) -> Task: ...
    def add_summary_task(self, summary_task: SummaryTask) -> SummaryTask: ...
    def delete(self, task: Task) -> None: ...


#----------------------------------------------
# ajut watcher
#------------------------------------------
class ISummaryTaskRepository(Protocol):
    def list_user_ids(self) -> list[int]: ...
    def claim_pending(self, limit: int) -> list[SummaryTask]: ...
    def mark_processed(self, summary_task_id: int) -> None: ...
    def mark_failed(self, summary_task_id: int, reason: str) -> None: ...
    def reset_stale_processing(self, before: datetime) -> int: ...
    def create_tasks_for_users(
        self,
        *,
        summary_task_id: int,
        user_ids: list[int],
        name: str,
        description: str,
        current_date: datetime,
    ) -> int: ...
#----------------------------------------------
# ajut watcher
#------------------------------------------
