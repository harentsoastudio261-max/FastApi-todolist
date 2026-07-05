"""SQLAlchemy database engine and session factory."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

# Logger dedie a la couche base de donnees pour tracer les incidents de session.
logger = get_logger(__name__)

# Engine SQLAlchemy partage par toute l'application.
# On le configure avec le cache connection pool et le mode debug pilote par la config.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.app_debug,
    future=True,
)

# Fabrique de sessions SQLAlchemy liee a l'engine.
# autocommit=False : on controle les transactions manuellement.
# autoflush=False : on evite les flush implicites avant d'etre pret.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

# Base declarative commune a tous les models SQLAlchemy.
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped session and closes it after use."""
    # Cree une session neuve pour la requete courante.
    db = SessionLocal()
    try:
        # Fournit la session a FastAPI, puis reprend la main apres la requete.
        yield db
        # Si la requete a reussi, on valide les insert/update/delete faits avec cette session.
        db.commit()
    except AppException:
        # Une erreur metier peut annuler la requete sans etre une panne de base de donnees.
        db.rollback()
        raise
    except Exception:
        # En cas d'erreur technique durant la requete, on annule les changements non valides.
        db.rollback()
        logger.exception("Database session error, rolling back")
        raise
    finally:
        # On ferme toujours la connexion pour eviter les fuites de ressources.
        db.close()
