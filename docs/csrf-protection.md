# Protection CSRF

Les cookies `access_token` et `refresh_token` sont envoyes automatiquement par le navigateur. Toute methode d'ecriture (`POST`, `PUT`, `PATCH`, `DELETE`) est donc controlee par `CsrfMiddleware` avant d'atteindre les routeurs ou les controllers.

## Flux

1. Le frontend demande `GET /auth/csrf`.
2. Le backend genere une valeur aleatoire, la place dans un cookie `HttpOnly` et la retourne dans le JSON.
3. Le frontend conserve la valeur en memoire et l'envoie dans `X-CSRF-Token` pour chaque ecriture.
4. Le middleware compare le cookie et l'en-tete avec une comparaison en temps constant. Une absence ou une difference retourne `403 csrf_validation_failed`.

Le jeton est renouvele apres le login et le refresh. Il est supprime au logout. Les reponses qui retournent un jeton utilisent `Cache-Control: no-store`.

## Configuration

Les variables suivantes sont definies dans `.env.example` :

- `CSRF_COOKIE_NAME`
- `CSRF_HEADER_NAME`
- `CSRF_COOKIE_SECURE`
- `CSRF_COOKIE_SAMESITE`
- `CSRF_TOKEN_EXPIRE_SECONDS`

En production HTTPS, definir `CSRF_COOKIE_SECURE=true` et conserver une politique `SameSite` compatible avec le frontend autorise.
