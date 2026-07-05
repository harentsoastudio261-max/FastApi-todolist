"""Contracts for AI task idea providers."""
from typing import Protocol

from app.schemas import GeneratedTaskIdea, TaskCreationType


class TaskIdeaProvider(Protocol):
    def generate_task_idea(self, task_type: TaskCreationType) -> GeneratedTaskIdea:
        ...