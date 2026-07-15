# Auth production: access token, refresh token, rotation et logout serveur

Ce document explique les modifications ajoutees au backend pour passer d'une authentification simple avec seulement un access token a un systeme plus complet et plus proche d'un usage production.

## Objectif

Avant, le login renvoyait seulement un `access_token`. Quand ce token expirait, l'utilisateur devait refaire un login complet.

Maintenant, le backend gere deux tokens :

- `access_token` : token JWT court, utilise pour appeler les routes protegees.
- `refresh_token` : token long, opaque, stocke cote serveur sous forme de hash, utilise pour obtenir une nouvelle paire de tokens.

Ce systeme permet :

- de limiter la duree de vie de l'access token ;
- de renouveler une session sans redemander le mot de passe ;
- de faire un logout cote serveur ;
- de faire une rotation des refresh tokens ;
- de revoquer toutes les sessions d'un utilisateur si necessaire.

## Fichiers modifies

### `app/models/entities.py`

Ajout du modele SQLAlchemy `RefreshToken`.

Cette table stocke les refresh tokens actifs ou revoques :

- `id` : identifiant du token en base.
- `user_id` : utilisateur proprietaire du token.
- `token_hash` : hash SHA-256 du refresh token, jamais le token brut.
- `expires_at` : date d'expiration du refresh token.
- `revoked_at` : date de revocation si le token a ete invalide.
- `replaced_by_hash` : hash du nouveau refresh token quand une rotation a eu lieu.
- `created_at` : date de creation.

La relation `User.refresh_tokens` a aussi ete ajoutee pour relier un utilisateur a ses sessions.

## `app/core/security.py`

Ajout de fonctions dediees aux refresh tokens :

```python
generate_refresh_token()
hash_refresh_token(token)
refresh_token_expires_at()
```

Le refresh token est volontairement opaque : ce n'est pas un JWT. C'est une chaine aleatoire generee avec `secrets.token_urlsafe()`.

Le serveur stocke uniquement son hash :

```python
sha256(token.encode("utf-8")).hexdigest()
```

Pourquoi stocker un hash ?

Si la base de donnees fuit, un attaquant ne peut pas utiliser directement les refresh tokens stockes, parce que les vrais tokens ne sont jamais sauvegardes en clair.

Le JWT d'access token contient aussi :

```json
{
  "typ": "access"
}
```

Cela permet de refuser un token qui ne serait pas du bon type.

## `app/schemas/__init__.py`

Le schema `Token` renvoie maintenant :

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

Deux nouveaux schemas ont ete ajoutes :

```python
class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str | None = None
    logout_all: bool = False
```

`RefreshTokenRequest` sert pour `/auth/refresh`.

`LogoutRequest` sert pour `/auth/logout`.

## `app/repositories/__init__.py`

Ajout du repository `RefreshTokenRepository`.

Il gere uniquement l'acces base de donnees pour les refresh tokens :

- chercher un refresh token par hash ;
- ajouter un refresh token ;
- revoquer un refresh token ;
- revoquer tous les refresh tokens d'un utilisateur.

Cette logique est dans le repository parce qu'elle concerne la persistence, pas la logique metier.

## `app/services/user_service.py`

Le service utilisateur gere maintenant toute la logique auth :

### Login

Quand l'utilisateur se connecte :

1. Le service verifie l'email et le mot de passe.
2. Il cree un `access_token`.
3. Il genere un `refresh_token` opaque.
4. Il stocke le hash du refresh token en base.
5. Il renvoie la paire au client.

### Refresh

Quand le client appelle `/auth/refresh` :

1. Le backend hash le refresh token recu.
2. Il cherche ce hash en base.
3. Il verifie que le token existe, n'est pas revoque, et n'est pas expire.
4. Il genere un nouveau refresh token.
5. Il revoque l'ancien token.
6. Il stocke le nouveau hash.
7. Il renvoie une nouvelle paire `access_token + refresh_token`.

C'est la rotation des refresh tokens.

### Logout

Quand le client appelle `/auth/logout` :

- avec `logout_all=false`, seul le refresh token fourni est revoque ;
- avec `logout_all=true`, tous les refresh tokens de l'utilisateur sont revoques.

Le logout demande aussi un access token valide dans le header :

```http
Authorization: Bearer <access_token>
```

## `app/controllers/auth_controller.py`

Le controller expose maintenant :

- `login()` ;
- `refresh()` ;
- `logout()`.

Il reste fin : il delegue la vraie logique au `UserService`.

## `app/routers/auth_router.py`

Nouvelles routes disponibles :

```http
POST /auth/login
POST /auth/refresh
POST /auth/logout
```

### `POST /auth/login`

Body :

```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

Response :

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

### `POST /auth/refresh`

Body :

```json
{
  "refresh_token": "..."
}
```

Response :

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

Important : apres un refresh, l'ancien refresh token ne doit plus etre utilise.

### `POST /auth/logout`

Headers :

```http
Authorization: Bearer <access_token>
```

Body pour deconnecter une seule session :

```json
{
  "refresh_token": "...",
  "logout_all": false
}
```

Body pour deconnecter toutes les sessions :

```json
{
  "logout_all": true
}
```

Response :

```http
204 No Content
```

## `app/core/config.py`

Ajout de la configuration :

```python
refresh_token_expire_days: int = 30
```

Elle permet de controler la duree de vie des refresh tokens depuis `.env`.

## `.env` et `.env.example`

Ajout de :

```env
REFRESH_TOKEN_EXPIRE_DAYS=30
```

## Flux complet

### Login

```txt
Client -> POST /auth/login
Backend -> verifie email/password
Backend -> cree access_token
Backend -> cree refresh_token
Backend -> stocke hash(refresh_token)
Backend -> renvoie access_token + refresh_token
```

### Requete protegee

```txt
Client -> Authorization: Bearer access_token
Backend -> decode access token
Backend -> identifie l'utilisateur courant
Backend -> execute la route
```

### Refresh

```txt
Client -> POST /auth/refresh avec refresh_token
Backend -> hash(refresh_token)
Backend -> verifie en base
Backend -> revoque l'ancien refresh token
Backend -> cree un nouveau refresh token
Backend -> renvoie une nouvelle paire
```

### Logout

```txt
Client -> POST /auth/logout avec access_token + refresh_token
Backend -> identifie l'utilisateur courant
Backend -> revoque le refresh token
Backend -> le client supprime ses tokens localement
```

## Pourquoi ce systeme est meilleur

Un access token seul est simple, mais impossible a revoquer proprement avant son expiration.

Avec refresh token stocke cote serveur :

- on peut fermer une session ;
- on peut fermer toutes les sessions ;
- on peut detecter les refresh tokens deja revoques ;
- on reduit le risque si un access token expire rapidement ;
- on garde une experience utilisateur fluide.

## Limites restantes

Ce systeme est plus solide, mais pour une vraie production il faudrait encore ajouter :

- Alembic pour migrer proprement la nouvelle table `refresh_tokens` ;
- stockage frontend securise selon le type d'application ;
- surveillance des refresh tokens reutilises apres rotation ;
- logs de securite plus structures.
