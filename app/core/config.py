"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Charge les variables depuis `.env`, ignore les champs inconnus,
    # et rend la config insensible a la casse pour simplifier l'usage local et en deployment.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    # Nom lisible de l'application, utilise par exemple dans les logs ou la doc.
    app_name: str = "FastAPI TodoList"
    # Environnement courant pour ajuster certains comportements.
    app_env: str = "development"
    # Active ou non les details de debug.
    app_debug: bool = True
    # Adresse sur laquelle le serveur ecoute.
    app_host: str = "0.0.0.0"
    # Port HTTP du service.
    app_port: int = 8000

    # JWT / Auth
    # Cle secrete utilisee pour signer et verifier les tokens JWT.
    jwt_secret: str = "change-me"
    # Algorithme de signature JWT.
    jwt_algorithm: str = "HS256"
    # Duree de validite d'un access token.
    jwt_access_token_expire_minutes: int = 60
    # Duree de validite d'un refresh token stocke cote serveur.
    refresh_token_expire_days: int = 30
    # Nom du cookie qui transporte l'access token.
    access_token_cookie_name: str = "access_token"
    # Nom du cookie qui transporte le refresh token.
    refresh_token_cookie_name: str = "refresh_token"
    # En local HTTP, False. En production HTTPS, mettre True.
    auth_cookie_secure: bool = False
    # Protection navigateur contre l'envoi cross-site des cookies.
    auth_cookie_samesite: str = "lax"

    # Database
    # Driver SQLAlchemy pour MySQL avec le connecteur pymysql.
    db_driver: str = "mysql+pymysql"
    # Utilisateur de la base de donnees.
    db_user: str = "root"
    # Mot de passe de la base de donnees.
    db_password: str = ""
    # Hote MySQL.
    db_host: str = "localhost"
    # Port MySQL.
    db_port: int = 3306
    # Nom de la base.
    db_name: str = "todolist"

    # AI provider
    # Provider IA utilise par la creation automatique de taches.
    ai_provider: str = "gemini"
    # Cle API Gemini. Peut aussi etre lue directement par le SDK depuis GEMINI_API_KEY.
    gemini_api_key: str | None = None
    # Modele Gemini utilise pour generer les noms et descriptions de taches.
    gemini_model: str = "gemini-3.5-flash"

    #----------------------------------------------
    # ajut watcher
    #------------------------------------------
    # Intervalle entre deux scans de la table summary_task.
    summary_task_watcher_interval_seconds: int = 2
    # Nombre maximum de summary_task traitees par iteration.
    summary_task_watcher_batch_size: int = 20
    # Delai apres lequel une ligne bloquee en processing est reprise.
    summary_task_processing_timeout_seconds: int = 300
    # A garder False en production si un worker separe est lance.
    enable_summary_task_watcher_in_api: bool = False
    #----------------------------------------------
    # ajut watcher
    #------------------------------------------

    # Logging
    # Niveau de log principal.
    log_level: str = "INFO"
    # Format des lignes de log.
    log_format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    @property
    def database_url(self) -> str:
        # Construit une URL SQLAlchemy unique a partir des parametres de config.
        return (
            f"{self.db_driver}://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    # Cache l'instance pour eviter de relire les variables d'environnement a chaque import.
    return Settings()


# Instance globale de configuration partagee dans l'application.
settings = get_settings()