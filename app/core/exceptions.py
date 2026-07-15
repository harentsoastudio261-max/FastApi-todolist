"""Custom application exceptions with HTTP-aware semantics."""
from fastapi import status


# Classe de base pour toutes les exceptions metier de l'application.
# Elle centralise le code HTTP, le message humain et un code d'erreur stable pour le client.
class AppException(Exception):
    # Valeur HTTP par defaut si une sous-classe ne la remplace pas.
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    # Message lisible qui sera renvoye au client.
    detail: str = "Internal server error"
    # Code machine lisible pour identifier l'erreur sans dependre du texte.
    error_code: str = "internal_error"

    def __init__(self, detail: str | None = None, error_code: str | None = None):
        # Permet a chaque cas d'erreur de personnaliser le message ou le code.
        if detail:
            self.detail = detail
        if error_code:
            self.error_code = error_code
        super().__init__(self.detail)


# Erreur quand une ressource attendue n'existe pas.
# Utilisee pour distinguer un vrai manque de ressource d'une autre erreur serveur.
class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found"
    error_code = "not_found"


# Erreur quand l'etat courant entre en conflit avec l'operation demandee.
# Typiquement utile pour les doublons ou les contraintes metier.
class ConflictException(AppException):
    status_code = status.HTTP_409_CONFLICT
    detail = "Conflict with current state"
    error_code = "conflict"


# Erreur quand l'utilisateur n'est pas authentifie.
# Elle correspond a un probleme d'identite ou de token invalide/manquant.
class UnauthorizedException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    detail = "Authentication required"
    error_code = "unauthorized"


# Erreur quand l'utilisateur est authentifie mais n'a pas les droits suffisants.
# On la separe de l'authentification pour bien distinguer identite et autorisation.
class ForbiddenException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Not enough permissions"
    error_code = "forbidden"


class RateLimitExceededException(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    detail = "Too many requests"
    error_code = "rate_limit_exceeded"

    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = retry_after_seconds
        super().__init__()


# Erreur quand les donnees fournies ne respectent pas les regles attendues.
# Utile pour des validations applicatives en plus de la validation automatique FastAPI.
class ValidationException(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    detail = "Validation error"
    error_code = "validation_error"


# Erreur generique quand la couche base de donnees echoue.
# Elle permet d'uniformiser les erreurs techniques au lieu de laisser remonter des details bruts.
class DatabaseException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail = "Database error"
    error_code = "database_error"


# Erreur quand le provider IA est indisponible, mal configure, ou renvoie une reponse invalide.
# Le client comprend que la creation de tache par IA a echoue sans exposer les details sensibles.
class AIProviderException(AppException):
    status_code = status.HTTP_502_BAD_GATEWAY
    detail = "AI provider error"
    error_code = "ai_provider_error"
