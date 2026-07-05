"""FastAPI dependencies: current user extraction from auth cookies."""
from fastapi import Cookie, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedException
from app.core.security import decode_access_token
from app.managers import ServiceManager, build_manager
from app.models.entities import User

# {
#   "function": "get_manager",
#   "purpose": "Construire et retourner le manager de services pour la requete courante.",
#   "inputs": {
#     "db": {
#       "type": "Session",
#       "source": "Depends(get_db)",
#       "meaning": "Session SQLAlchemy fournie par FastAPI"
#     }
#   },
#   "returns": {
#     "type": "ServiceManager",
#     "meaning": "Objet central qui regroupe les services applicatifs"
#   },
#   "why": "On fait cela ici pour centraliser la creation du contexte applicatif autour de la session DB. Le routeur ne devrait pas construire lui-meme les objets metier, et le service ne devrait pas dependre de la facon dont FastAPI injecte les dependances. Cette fonction fournit donc un point d entree reutilisable pour toute route qui a besoin du gestionnaire."
# }
def get_manager(db: Session = Depends(get_db)) -> ServiceManager:
    return build_manager(db)


# {
#   "function": "_extract_token_from_cookie",
#   "purpose": "Extraire l'access token depuis le cookie HTTP securise.",
#   "inputs": {
#     "access_token": {
#       "type": "str | None",
#       "meaning": "Valeur du cookie access_token envoye automatiquement par le navigateur"
#     }
#   },
#   "returns": {
#     "type": "str",
#     "meaning": "JWT access token pret a etre decode"
#   },
#   "errors": [
#     {
#       "type": "UnauthorizedException",
#       "when": "Cookie absent ou vide"
#     }
#   ],
#   "why": "On lit le token depuis un cookie HttpOnly pour eviter de le stocker dans localStorage et de le rendre lisible par JavaScript. Le navigateur envoie ce cookie automatiquement avec la requete, et cette dependance garde la lecture du contexte HTTP hors des services metier."
# }
def _extract_token_from_cookie(access_token: str | None) -> str:
    if not access_token:
        raise UnauthorizedException("Missing access token cookie", "missing_access_cookie")
    return access_token


# {
#   "function": "get_current_user",
#   "purpose": "Verifier le token du cookie, charger l'utilisateur courant et le retourner.",
#   "inputs": {
#     "access_token": {
#       "type": "str | None",
#       "source": "Cookie(default=None)",
#       "meaning": "Cookie HttpOnly contenant le JWT access token"
#     },
#     "manager": {
#       "type": "ServiceManager",
#       "source": "Depends(get_manager)",
#       "meaning": "Acces aux services applicatifs"
#     }
#   },
#   "returns": {
#     "type": "User",
#     "meaning": "Utilisateur authentifie"
#   },
#   "errors": [
#     {
#       "type": "UnauthorizedException",
#       "when": "Token absent, invalide, expire, ou utilisateur introuvable"
#     }
#   ],
#   "why": "On garde cette logique dans deps parce qu'elle depend directement du contexte HTTP et de l'injection FastAPI. Le controller devrait recevoir un utilisateur deja resolu, pas s'occuper de lire le cookie, decoder le JWT et chercher l'utilisateur en base. En separant ainsi, on garde les routes plus propres, on reutilise l'authentification partout, et on laisse la logique metier vivre dans les couches service/controller."
# }
def get_current_user(
    access_token: str | None = Cookie(default=None, alias=settings.access_token_cookie_name),
    manager: ServiceManager = Depends(get_manager),
) -> User:
    token = _extract_token_from_cookie(access_token)
    payload = decode_access_token(token)
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError):
        raise UnauthorizedException("Invalid token payload", "invalid_token")

    user = manager.user_service.repo.get_by_id(user_id)
    if user is None:
        raise UnauthorizedException("User no longer exists", "user_not_found")
    return user


# Pourquoi ces fonctions sont ici et pas dans controller/service/router :
# - deps.py contient des dependances reutilisables de FastAPI via Depends() et Cookie().
# - Le router doit rester concentre sur les routes HTTP et la liaison URL -> fonction.
# - Le controller/service doit porter la logique metier, pas la lecture des cookies HTTP ni la creation automatique des objets de requete.
# - Ici, on isole l'authentification par cookie, la construction du manager, et la recuperation de l'utilisateur courant pour pouvoir les reutiliser dans plusieurs routes sans dupliquer le code.
