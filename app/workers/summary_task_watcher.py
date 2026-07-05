"""Process entrypoint for the summary_task watcher."""
import signal
from threading import Event
from types import FrameType

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger, setup_logging
from app.services.summary_task_processor import build_summary_task_processor

logger = get_logger(__name__)


def build_stop_event_from_signals() -> Event:
    """Create the stop signal used by the watcher process.

    Who uses it:
    - `run()` uses it when the watcher is started as a standalone process.
    - `app.main.lifespan()` can pass its own event when the watcher is embedded
      inside the API process for development.

    Why it exists:
    - it gives the watcher a clean way to stop on `SIGINT` and `SIGTERM`;
    - it avoids killing the process abruptly while a DB iteration is running;
    - it keeps shutdown behavior centralized in one place.
    """
    stop_event = Event()

    def handle_signal(signum: int, frame: FrameType | None) -> None:
        """Signal handler that flips the stop flag.

        Who calls it:
        - the operating system through Python's `signal` module.

        Why it exists:
        - when the process receives Ctrl+C or a container stop signal, the
          watcher needs to stop after the current iteration instead of exiting
          in the middle of a DB transaction.
        """
        logger.info("summary_task_watcher received stop signal=%s", signum)
        stop_event.set()

    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(signum, handle_signal)
        except (AttributeError, ValueError):
            logger.debug("summary_task_watcher cannot register signal=%s", signum)

    return stop_event


def run_iteration() -> int:
    """Run one polling cycle against the database.

    Who uses it:
    - `run()` calls it on every loop tick.

    What it does:
    - opens a fresh SQLAlchemy session;
    - builds the summary-task processor service;
    - processes one batch of pending rows;
    - commits on success or rolls back on failure.

    Why it is isolated:
    - the work for one pass is easier to test;
    - the DB session lifetime stays short;
    - failures stay local to one iteration, not the whole watcher process.
    """
    with SessionLocal() as db:
        try:
            processor = build_summary_task_processor(db)
            handled_count = processor.process_pending_batch()
            db.commit()
            logger.info("summary_task_watcher iteration committed handled_rows=%s", handled_count)
            return handled_count
        except Exception:
            db.rollback()
            logger.exception("summary_task_watcher iteration failed and rolled back")
            return 0


def run(stop_event: Event | None = None) -> None:
    """Main watcher loop.

    Who uses it:
    - `python -m app.workers.summary_task_watcher` calls `main()`, which calls
      this function.
    - `app.main.lifespan()` can also call it in a background thread when the
      watcher is embedded in the API process.

    What it does:
    - initializes logging;
    - creates or reuses the stop event;
    - runs `run_iteration()` every few seconds;
    - exits cleanly when the stop event is set.
    """
    setup_logging()
    active_stop_event = stop_event or build_stop_event_from_signals()
    logger.info(
        "summary_task_watcher started interval_seconds=%s batch_size=%s timeout_seconds=%s",
        settings.summary_task_watcher_interval_seconds,
        settings.summary_task_watcher_batch_size,
        settings.summary_task_processing_timeout_seconds,
    )

    while not active_stop_event.is_set():
        run_iteration()
        active_stop_event.wait(settings.summary_task_watcher_interval_seconds)

    logger.info("summary_task_watcher stopped")


def main() -> None:
    """Console entrypoint for the watcher module.

    Who uses it:
    - Python calls it when the module is executed with `-m`.

    Why it exists:
    - it keeps the file runnable as a standalone worker process without any
      extra bootstrap script.
    """
    run()


if __name__ == "__main__":
    main()