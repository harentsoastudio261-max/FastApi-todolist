"""Prompt helpers for AI task creation."""
from app.core.exceptions import AIProviderException
from app.schemas import TaskCreationType


def build_task_creation_prompt(task_type: TaskCreationType) -> str:
    if task_type == TaskCreationType.HOBBIES:
        context = "personal hobby"
        quality = "concrete, enjoyable, and doable today"
    elif task_type == TaskCreationType.WORK:
        context = "professional work"
        quality = "concrete, productive, and doable today"
    else:
        raise AIProviderException("Unsupported task creation type", "unsupported_task_creation_type")

    return (
        f"Generate one useful {context} task. "
        "Return only JSON with these fields: "
        "name: short task title, max 255 characters; "
        "description: practical task description. "
        f"The task must be {quality}."
    )