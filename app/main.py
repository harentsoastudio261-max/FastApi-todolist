"""Application entrypoint. Wires routers, exception handlers, and DB init."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.database import Base, engine
from app.core.exception_handlers import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.routers.auth_router import router as auth_router
from app.routers.task_router import router as task_router

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s (env=%s)", settings.app_name, settings.app_env)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ensured")
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="Layered FastAPI TodoList — reference architecture.",
    version="1.0.0",
    debug=settings.app_debug,
    lifespan=lifespan,
)

register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(task_router)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name}
