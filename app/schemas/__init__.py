"""Pydantic schemas — REST DTOs and the mappers between REST and domain models."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.entities import Task, User
from app.models.enums import Priority


# ------------------------------------------------------------------
# Auth / User schemas
# ------------------------------------------------------------------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str | None
    created_at: datetime


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ------------------------------------------------------------------
# Task schemas
# ------------------------------------------------------------------
class TaskBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    priority: Priority = Priority.MEDIUM

    @field_validator("end_date")
    @classmethod
    def _end_after_start(cls, end_date: datetime | None, info) -> datetime | None:
        start_date = info.data.get("start_date")
        if start_date and end_date and end_date < start_date:
            raise ValueError("end_date must be after start_date")
        return end_date


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    priority: Priority | None = None

    @field_validator("end_date")
    @classmethod
    def _end_after_start(cls, end_date: datetime | None, info) -> datetime | None:
        start_date = info.data.get("start_date")
        if start_date and end_date and end_date < start_date:
            raise ValueError("end_date must be after start_date")
        return end_date


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: str | None
    start_date: datetime | None
    end_date: datetime | None
    priority: Priority
    created_at: datetime
    updated_at: datetime


# ------------------------------------------------------------------
# Mappers: REST <-> ORM model
# ------------------------------------------------------------------
def task_to_read(task: Task) -> TaskRead:
    return TaskRead.model_validate(task)


def user_to_read(user: User) -> UserRead:
    return UserRead.model_validate(user)


def task_create_to_model(data: TaskCreate, user_id: int) -> Task:
    return Task(
        user_id=user_id,
        name=data.name,
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
        priority=data.priority,
    )


def apply_task_update(task: Task, data: TaskUpdate) -> Task:
    """Apply partial update fields onto an existing Task in place."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    return task
