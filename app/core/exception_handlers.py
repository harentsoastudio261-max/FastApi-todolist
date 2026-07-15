"""Global exception handlers translating app exceptions to JSON responses."""
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions import AppException, DatabaseException, RateLimitExceededException
from app.core.logging import get_logger

# Logger centralise pour tracer les erreurs globales de l'application.
logger = get_logger(__name__)


# Construit une reponse JSON standardisee pour toutes les erreurs de l'application.
# On garde ici un format unique pour que le client recoive toujours la meme structure.
def _error_response(
    status_code: int,
    detail: str,
    error_code: str,
    extra: dict | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    # Structure commune de reponse d'erreur.
    payload = {"error": {"code": error_code, "message": detail}}
    if extra:
        # Ajoute des details supplementaires quand on veut exposer davantage de contexte.
        payload["error"]["details"] = extra
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload), headers=headers)


# Enregistre tous les handlers d'erreurs globaux sur l'application FastAPI.
# Cela permet de convertir les exceptions techniques ou metier en JSON propre.
def register_exception_handlers(app: FastAPI) -> None:
    # Intercepte les exceptions metier de l'application.
    # Elles portent deja leur code HTTP et leur code d'erreur applicatif.
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        # Niveau warning car l'erreur est geree par le flux normal de l'application.
        logger.warning("AppException %s on %s %s: %s", exc.error_code, request.method, request.url.path, exc.detail)
        headers = None
        if isinstance(exc, RateLimitExceededException):
            headers = {"Retry-After": str(exc.retry_after_seconds)}
        return _error_response(exc.status_code, exc.detail, exc.error_code, headers=headers)

    # Intercepte les erreurs de validation FastAPI / Pydantic.
    # On renvoie une reponse claire au client avec la liste des champs invalides.
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.info("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Request validation failed",
            "validation_error",
            extra=exc.errors(),
        )

    # Intercepte les conflits d'integrite SQL, par exemple doublon d'unicite ou contrainte violee.
    # Cela arrive souvent quand la base refuse une ecriture invalide.
    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        logger.exception("Integrity error on %s %s", request.method, request.url.path)
        return _error_response(
            status.HTTP_409_CONFLICT,
            "Data integrity conflict (duplicate or constraint violation)",
            "conflict",
        )

    # Intercepte les autres erreurs SQLAlchemy non prevues.
    # On les enveloppe dans une exception applicative pour garder une sortie uniforme.
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Database error on %s %s", request.method, request.url.path)
        wrapped = DatabaseException(str(exc))
        return _error_response(wrapped.status_code, wrapped.detail, wrapped.error_code)

    # Dernier filet de securite pour tout ce qui n'a pas ete capture ailleurs.
    # On evite ainsi de renvoyer des erreurs brutes ou des traces sensibles au client.
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error",
            "internal_error",
        )
