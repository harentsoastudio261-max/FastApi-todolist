"""Centralized logging configuration."""
import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """Configure root logger once at application startup."""
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(settings.log_format))
    root.addHandler(handler)
    root.setLevel(settings.log_level)

    # Quiet noisy libraries
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING if not settings.app_debug else logging.INFO)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
