"""Helpers for parsing summary_task payloads."""


class SummaryTaskFormatError(ValueError):
    """Raised when summary_task.all_task cannot be parsed into a task."""


def parse_summary_task_text(value: str) -> tuple[str, str]:
    if "||" not in value:
        raise SummaryTaskFormatError("summary_task.all_task must contain '||'")

    name, description = value.split("||", 1)
    name = name.strip()
    description = description.strip()

    if not name:
        raise SummaryTaskFormatError("summary_task.all_task task name is required")

    return name, description