"""Manager layer - coordinates a DB session, repositories, services, and use cases.

Controllers depend only on this, keeping them thin and testable.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.providers.ai.factory import build_task_idea_provider
from app.repositories import RefreshTokenRepository, TaskRepository, UserRepository
from app.services.hobbies_task_creation_service import HobbiesTaskCreationService
from app.services.rate_limit_service import build_rate_limit_service
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.services.work_task_creation_service import WorkTaskCreationService
from app.use_cases.task_creation_use_case import TaskCreationUseCase


# Ce fichier vit dans `__init__.py` pour exposer directement la couche manager
# au niveau du package `app.managers`.
# Cela permet des imports simples comme `from app.managers import ServiceManager, build_manager`
# sans avoir a viser un sous-module supplementaire.
# C'est pratique pour un point d'entree central qui assemble la session DB,
# les repositories, les services et les use cases de la requete courante.
@dataclass
class ServiceManager:
    # Objet de coordination par requete.
    # Il regroupe les services metier qui partagent la meme session SQLAlchemy.
    # @dataclass genere automatiquement __init__, __repr__, __eq__ et facilite
    # la creation d'un objet simple de transport/assemblage sans code boilerplate.
    """Holds the per-request service and use-case instances sharing one session."""
    user_service: UserService
    task_service: TaskService
    task_creation_use_case: TaskCreationUseCase
    db: Session


# Fabrique le manager complet a partir d'une session SQLAlchemy deja ouverte.
# Cette fonction instancie d'abord les repositories, puis les providers/services,
# puis les regroupe dans un seul objet ServiceManager.
# On centralise cette logique ici pour eviter de la dupliquer dans les controllers,
# et pour garantir que toutes les couches de la requete utilisent la meme session.
def build_manager(db: Session) -> ServiceManager:
    # Chaque repository parle directement a la base via la meme session.
    user_repo = UserRepository(db)
    refresh_token_repo = RefreshTokenRepository(db)
    task_repo = TaskRepository(db)
    rate_limiter = build_rate_limit_service()

    task_idea_provider = build_task_idea_provider(settings)
    hobbies_task_creation_service = HobbiesTaskCreationService(task_repo, task_idea_provider)
    work_task_creation_service = WorkTaskCreationService(task_repo, task_idea_provider)
    task_creation_use_case = TaskCreationUseCase(
        hobbies_task_creation_service,
        work_task_creation_service,
        rate_limiter,
    )

    return ServiceManager(
        user_service=UserService(user_repo, refresh_token_repo, rate_limiter),
        task_service=TaskService(task_repo, rate_limiter),
        task_creation_use_case=task_creation_use_case,
        db=db,
    )
