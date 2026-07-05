"""Centralized logging configuration."""
import logging
import sys

from app.core.config import settings


# Configure le logger racine une seule fois au demarrage de l'application.
# Cela garantit un format de log unique et un comportement coherent dans tous les modules.
def setup_logging() -> None:
    """Configure root logger once at application startup."""
    # On evite de reconfigurer le logging si un handler existe deja.
    root = logging.getLogger()
    if root.handlers:
        return

    # Envoie les logs vers la sortie standard pour qu'ils soient visibles par le serveur et les conteneurs.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(settings.log_format))
    root.addHandler(handler)
    root.setLevel(settings.log_level)

    # Rend certains logs de bibliotheques moins bavards pour garder les messages utiles.
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING if not settings.app_debug else logging.INFO)


# Retourne un logger nomme pour le module appelant.
# On l'utilise partout pour avoir des traces lisibles et identifiables par composant.
def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
