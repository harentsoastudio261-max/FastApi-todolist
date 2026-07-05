# Database

Ce document montre a quoi ressemble la base de donnees actuelle du projet.

## Vue d'ensemble

La base est construite a partir des modeles SQLAlchemy definis dans [entities.py](</C:/Users/Harentsoa/Desktop/INFO-Generale/Learning/FastAPI - Mysql - Rag - course/app/models/entities.py:1>).

Les tables sont creees automatiquement au demarrage de l'application dans [main.py](</C:/Users/Harentsoa/Desktop/INFO-Generale/Learning/FastAPI - Mysql - Rag - course/app/main.py:18>) avec :

```python
Base.metadata.create_all(bind=engine)
```

## Schema relationnel

```text
users
  1 ---- n tasks
  1 ---- n refresh_tokens

summary_task
  table independante
```

```text
users
- id (PK)
- email (UNIQUE, INDEX)
- hashed_password
- full_name
- created_at
- updated_at

tasks
- id (PK)
- user_id (FK -> users.id, INDEX)
- name
- description
- start_date
- end_date
- priority
- created_at
- updated_at

summary_task
- id (PK)
- all_task (TEXT)

refresh_tokens
- id (PK)
- user_id (FK -> users.id, INDEX)
- token_hash (UNIQUE, INDEX)
- expires_at
- revoked_at
- replaced_by_hash
- created_at
```

## Table `users`

Cette table stocke les comptes utilisateurs.

Colonnes principales :

- `id` : identifiant unique auto-incremente.
- `email` : email unique de l'utilisateur.
- `hashed_password` : mot de passe chiffre, jamais le mot de passe brut.
- `full_name` : nom complet optionnel.
- `created_at` : date de creation.
- `updated_at` : date de derniere mise a jour.

Role dans le projet :

- un utilisateur peut posseder plusieurs tasks.
- un utilisateur peut avoir plusieurs refresh tokens actifs ou anciens.

## Table `tasks`

Cette table stocke les taches de chaque utilisateur.

Colonnes principales :

- `id` : identifiant unique auto-incremente.
- `user_id` : proprietaire de la tache.
- `name` : nom de la tache.
- `description` : description libre, optionnelle.
- `start_date` : date de debut optionnelle.
- `end_date` : date de fin optionnelle.
- `priority` : priorite de la tache (`low`, `medium`, `high` selon l'enum Python).
- `created_at` : date de creation.
- `updated_at` : date de derniere modification.

Relation :

- plusieurs tasks peuvent appartenir a un seul user.
- si un user est supprime, ses tasks sont supprimees aussi via `ondelete="CASCADE"`.

## Table `summary_task`

Cette table stocke le contenu envoye a la route de resume des taches.

Colonnes principales :

- `id` : identifiant unique auto-incremente.
- `all_task` : texte du resume stocke en base.

Remarque :

- la requete HTTP envoie le champ `summary`.
- la base enregistre cette valeur dans la colonne `all_task`.

## Table `refresh_tokens`

Cette table stocke les refresh tokens de l'authentification.

Important :

- on ne stocke pas le refresh token brut.
- on stocke seulement son hash dans `token_hash`.

Colonnes principales :

- `id` : identifiant unique auto-incremente.
- `user_id` : utilisateur proprietaire du token.
- `token_hash` : hash unique du refresh token.
- `expires_at` : date d'expiration du refresh token.
- `revoked_at` : date de revocation si le token a ete invalide.
- `replaced_by_hash` : hash du nouveau token si rotation.
- `created_at` : date de creation.

Role dans le projet :

- permet la rotation des refresh tokens.
- permet le logout serveur.
- permet de revoquer une session precise ou toutes les sessions d'un utilisateur.

## Relations ORM

Dans SQLAlchemy, les relations sont definies ainsi :

- `User.tasks` <-> `Task.user`
- `User.refresh_tokens` <-> `RefreshToken.user`

Cela veut dire :

- depuis un `User`, on peut recuperer directement ses tasks.
- depuis un `User`, on peut recuperer directement ses refresh tokens.
- depuis une `Task`, on peut retrouver son user.
- depuis un `RefreshToken`, on peut retrouver son user.

## Representation simple

```text
Un user
  -> peut avoir 0..n tasks
  -> peut avoir 0..n refresh_tokens

Une task
  -> appartient a 1 seul user

Un summary_task
  -> est une ligne de texte independante

Un refresh_token
  -> appartient a 1 seul user
```

## Pourquoi cette structure ?

- `users` separe les donnees du compte.
- `tasks` separe les donnees metier de l'application Todo.
- `summary_task` ajoute un stockage dedie pour les resumes envoyes par la nouvelle route.
- `refresh_tokens` separe la gestion des sessions longues de l'utilisateur.

Cette structure est simple, claire, et deja adaptee a un backend avec :

- authentification JWT + refresh token,
- rotation des tokens,
- logout par session ou global,
- gestion des taches par utilisateur,
- stockage des resumes de taches.
