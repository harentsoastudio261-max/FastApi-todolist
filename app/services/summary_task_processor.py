"""Summary task processor - transforme les lignes summary_task en taches utilisateur."""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.entities import SummaryTask
from app.repositories import SummaryTaskRepository
from app.services.helpers.summary_task_parser import SummaryTaskFormatError, parse_summary_task_text

logger = get_logger(__name__)


# -----------------------------------------------------------------------------
# Service applicatif du watcher
# Ce service orchestre tout le traitement metier:
# - il reclasse les lignes bloquees trop longtemps,
# - il prend un lot de lignes en attente,
# - il parse chaque ligne,
# - il cree les taches pour tous les utilisateurs,
# - il marque la ligne comme traitee ou en echec.
# Il est appele par le worker `summary_task_watcher.py` et reste testeable sans
# FastAPI.
# -----------------------------------------------------------------------------
class SummaryTaskProcessorService:
    # -------------------------------------------------------------------------
    # Constructeur du service
    # Il recoit le repository et les parametres de fonctionnement du watcher.
    # Le worker lui fournit ces valeurs depuis la configuration globale.
    # -------------------------------------------------------------------------
    def __init__(
        self,
        repo: SummaryTaskRepository,
        *,
        batch_size: int,
        processing_timeout_seconds: int,
    ):
        self.repo = repo
        self.batch_size = batch_size
        self.processing_timeout_seconds = processing_timeout_seconds

    # -------------------------------------------------------------------------
    # Traitement d'un lot
    # Cette methode est appelee a chaque tour de boucle du watcher.
    # Elle sert a traiter un petit groupe de lignes `pending` sans bloquer le
    # process trop longtemps. C'est elle qui fait le lien entre la logique de
    # polling et la logique metier.
    # -------------------------------------------------------------------------
    def process_pending_batch(self) -> int:
        timeout_before = datetime.utcnow() - timedelta(seconds=self.processing_timeout_seconds)
        stale_count = self.repo.reset_stale_processing(timeout_before)
        if stale_count:
            logger.warning("summary_task_watcher reset stale processing rows count=%s", stale_count)

        summary_tasks = self.repo.claim_pending(self.batch_size)
        if not summary_tasks:
            logger.debug("summary_task_watcher no pending rows")
            return 0

        handled_count = 0
        for summary_task in summary_tasks:
            try:
                created_count = self._process_one(summary_task)
            except SummaryTaskFormatError as exc:
                self.repo.mark_failed(summary_task.id, str(exc))
                handled_count += 1
                logger.warning(
                    "summary_task_watcher failed format summary_task_id=%s reason=%s",
                    summary_task.id,
                    exc,
                )
                continue

            self.repo.mark_processed(summary_task.id)
            handled_count += 1
            logger.info(
                "summary_task_watcher processed summary_task_id=%s created_tasks=%s",
                summary_task.id,
                created_count,
            )

        return handled_count

    # -------------------------------------------------------------------------
    # Traitement d'une seule ligne summary_task
    # Cette methode prend une ligne deja reclamee, parse son contenu et demande
    # au repository de creer une tache par utilisateur. Elle isole la logique
    # de transformation pour garder `process_pending_batch()` lisible.
    # -------------------------------------------------------------------------
    def _process_one(self, summary_task: SummaryTask) -> int:
        name, description = parse_summary_task_text(summary_task.all_task)
        user_ids = self.repo.list_user_ids()
        current_date = datetime.utcnow()

        if not user_ids:
            logger.info("summary_task_watcher found no users summary_task_id=%s", summary_task.id)
            return 0

        created_count = self.repo.create_tasks_for_users(
            summary_task_id=summary_task.id,
            user_ids=user_ids,
            name=name,
            description=description,
            current_date=current_date,
        )
        logger.debug(
            "summary_task_watcher create task payload summary_task_id=%s users=%s created=%s",
            summary_task.id,
            len(user_ids),
            created_count,
        )
        return created_count


# -----------------------------------------------------------------------------
# Fabrique du service pour le worker
# Cette fonction construit l'objet metier avec la session courante et les
# valeurs de configuration. Le worker l'utilise pour rester tres fin: il ouvre
# la session, appelle cette fabrique, puis lance le traitement.
# -----------------------------------------------------------------------------
def build_summary_task_processor(db: Session) -> SummaryTaskProcessorService:
    return SummaryTaskProcessorService(
        SummaryTaskRepository(db),
        batch_size=settings.summary_task_watcher_batch_size,
        processing_timeout_seconds=settings.summary_task_processing_timeout_seconds,
    )