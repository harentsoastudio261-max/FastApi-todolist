"""Application entrypoint. Wires routers, exception handlers, and DB init."""
from contextlib import asynccontextmanager
from threading import Event, Thread

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, engine
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.middleware.csrf import CsrfMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.routers.auth_router import router as auth_router
from app.routers.task_creation_router import router as task_creation_router
from app.routers.task_router import router as task_router
from app.services.rate_limit_service import build_rate_limit_service
from app.workers.summary_task_watcher import run as run_summary_task_watcher


setup_logging()
logger = get_logger(__name__)


#----------------------------------------------
# ajut watcher
#------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    watcher_stop_event: Event | None = None
    watcher_thread: Thread | None = None

    logger.info("Starting %s (env=%s)", settings.app_name, settings.app_env)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")

    if settings.enable_summary_task_watcher_in_api:
        watcher_stop_event = Event()
        watcher_thread = Thread(
            target=run_summary_task_watcher,
            kwargs={"stop_event": watcher_stop_event},
            name="summary-task-watcher",
            daemon=True,
        )
        watcher_thread.start()
        logger.info("summary_task_watcher started inside API process")

    try:
        yield
    finally:
        if watcher_stop_event is not None and watcher_thread is not None:
            watcher_stop_event.set()
            watcher_thread.join(timeout=settings.summary_task_watcher_interval_seconds + 5)
            logger.info("summary_task_watcher stopped inside API process")
        logger.info("Shutting down %s", settings.app_name)
#----------------------------------------------
# ajut watcher
#------------------------------------------


app = FastAPI(
    title=settings.app_name,
    description="Layered FastAPI TodoList - reference architecture.",
    version="1.0.0",
    debug=settings.app_debug,
    lifespan=lifespan,
)

# CSRF protects every unsafe HTTP method before it can reach a router/controller.
app.add_middleware(
    CsrfMiddleware,
    cookie_name=settings.csrf_cookie_name,
    header_name=settings.csrf_header_name,
)

app.add_middleware(
    RateLimitMiddleware,
    rate_limiter=build_rate_limit_service(),
)

# CORS wraps the CSRF middleware so trusted frontend clients can read 403 JSON errors.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(task_router)
app.include_router(task_creation_router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}

# uvicorn app.main:app  
# python -m app.workers.summary_task_watcher
