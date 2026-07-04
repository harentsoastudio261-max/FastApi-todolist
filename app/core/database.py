"""SQLAlchemy database engine and session factory."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.app_debug,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        logger.exception("Database session error, rolling back")
        raise
    finally:
        db.close()
