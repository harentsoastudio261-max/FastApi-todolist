# Watcher `summary_task` vers `tasks`

Ce document explique comment ajouter proprement un watcher qui surveille la table
`summary_task` et transforme chaque nouvelle ligne en taches pour tous les
utilisateurs.

Dans le code actuel, la colonne s'appelle `all_task` dans le modele
`SummaryTask`. Si on parle de `task_all` dans une specification fonctionnelle,
il faut le lire ici comme `summary_task.all_task`, sauf si on decide de faire
une migration de renommage.

## Objectif fonctionnel

Quand une nouvelle ligne est ajoutee dans `summary_task` :

```text
all_task = "afjp || klehfahg"
```

le watcher cree une tache dans `tasks` pour chaque utilisateur existant :

- `name` = texte avant `||`, ici `afjp`
- `description` = texte apres `||`, ici `klehfahg`
- `start_date` = date courante
- `end_date` = date courante
- `priority` = `medium`
- `user_id` = l'identifiant de chaque utilisateur present en base

Le watcher doit tourner toutes les 2 secondes.

## Decision d'architecture

La solution recommandee est un process worker separe :

```bash
python -m app.workers.summary_task_watcher
```

Pourquoi :

- l'API FastAPI reste concentree sur les requetes HTTP ;
- le watcher peut etre demarre, arrete, redemarre et supervise separement ;
- en production, plusieurs workers API ne lancent pas chacun leur propre
  watcher ;
- les logs et erreurs du traitement asynchrone sont plus faciles a isoler.

Pour le developpement uniquement, on peut aussi demarrer ce watcher depuis le
`lifespan` FastAPI avec un flag de configuration, mais ce ne doit pas etre le
mode principal en production.

## Separation des responsabilites

On garde l'architecture actuelle du projet :

```text
worker
  -> service       logique metier de transformation
  -> repository    requetes SQLAlchemy
  -> model         tables SQLAlchemy
  -> core          config, DB, logging
```

Le watcher ne doit pas contenir la logique metier. Il doit seulement :

1. attendre 2 secondes entre deux tours ;
2. ouvrir une session DB ;
3. appeler un service de traitement ;
4. logger le resultat ;
5. gerer l'arret propre du process.

La logique de parsing et de creation des taches vit dans un service. Les
requêtes SQL vivent dans les repositories.

## Changements de donnees recommandes

La table `summary_task` actuelle contient seulement :

```text
id
all_task
```

Ce n'est pas suffisant pour un watcher fiable, car apres un redemarrage on ne
sait pas quelles lignes ont deja ete traitees. Il faut ajouter un etat
persistant.

Ajouts recommandes dans `SummaryTask` :

```text
status                 pending | processing | processed | failed
created_at             date de creation
processing_started_at  date de prise en charge par un watcher
processed_at           date de fin de traitement
processing_error       message court en cas d'echec
```

Valeur par defaut :

```text
status = pending
```

Ajout recommande dans `Task` :

```text
source_summary_task_id  FK nullable vers summary_task.id
```

avec une contrainte unique :

```text
unique(user_id, source_summary_task_id)
```

Cette contrainte rend le traitement idempotent : si le watcher redemarre au
mauvais moment, il ne recrée pas deux fois la meme tache pour le meme
utilisateur et le meme resume.

Pour une production reelle, ces changements doivent passer par Alembic. Le
`Base.metadata.create_all()` actuel est acceptable pour un projet local ou un
cours, mais ce n'est pas une strategie de migration production.

## Fichiers a ajouter ou modifier

### `app/models/entities.py`

Ajouter les colonnes de suivi sur `SummaryTask` et le lien optionnel depuis
`Task`.

Responsabilite : representer la structure persistante, pas traiter les lignes.

### `app/models/enums.py`

Ajouter un enum de statut :

```python
class SummaryTaskStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
```

### `app/repositories/__init__.py`

Ajouter un `SummaryTaskRepository` ou, si on veut rester tres proche du code
actuel, ajouter les methodes dans la zone repository existante.

Methodes utiles :

```python
list_user_ids()
claim_pending(limit: int) -> list[SummaryTask]
mark_processed(summary_task_id: int) -> None
mark_failed(summary_task_id: int, reason: str) -> None
reset_stale_processing(before: datetime) -> int
create_tasks_for_users(rows: list[dict]) -> int
```

Le repository cache les details SQLAlchemy : `select`, `update`, locks,
insertions en lot, etc.

### `app/services/summary_task_processor.py`

Ajouter un service dedie :

```python
class SummaryTaskProcessorService:
    def process_pending_batch(self) -> int:
        ...
```

Responsabilites :

- parser `all_task` ;
- verifier que le format contient `||` ;
- construire les taches pour tous les utilisateurs ;
- appliquer `Priority.MEDIUM` ;
- utiliser une seule date courante pour `start_date` et `end_date` ;
- marquer la ligne comme `processed` ou `failed`.

La fonction de parsing doit etre isolee et testable :

```python
def parse_summary_task_text(value: str) -> tuple[str, str]:
    name, description = value.split("||", 1)
    name = name.strip()
    description = description.strip()
    if not name:
        raise ValueError("Task name is required")
    return name, description
```

On utilise `split("||", 1)` pour autoriser `||` dans la description apres le
premier separateur.

### `app/workers/summary_task_watcher.py`

Ajouter le point d'entree du watcher.

Responsabilites :

- charger la configuration ;
- configurer les logs ;
- boucler tant que le process n'est pas arrete ;
- ouvrir une nouvelle session DB a chaque iteration ;
- appeler `SummaryTaskProcessorService` ;
- attendre `settings.summary_task_watcher_interval_seconds`.

Pseudo-code :

```python
def run() -> None:
    setup_logging()
    stop_event = build_stop_event_from_signals()

    while not stop_event.is_set():
        with SessionLocal() as db:
            try:
                service = build_summary_task_processor(db)
                processed_count = service.process_pending_batch()
                db.commit()
                logger.info("Summary task watcher processed %s rows", processed_count)
            except Exception:
                db.rollback()
                logger.exception("Summary task watcher iteration failed")

        stop_event.wait(settings.summary_task_watcher_interval_seconds)
```

### `app/core/config.py`

Ajouter une configuration explicite :

```python
summary_task_watcher_interval_seconds: int = 2
summary_task_watcher_batch_size: int = 20
summary_task_processing_timeout_seconds: int = 300
enable_summary_task_watcher_in_api: bool = False
```

L'intervalle de 2 secondes devient configurable sans modifier le code.

## Flux de traitement

```text
1. POST /tasks/summary cree une ligne summary_task avec status=pending
2. Le watcher se reveille
3. Il reclame un petit batch de lignes pending
4. Chaque ligne passe en processing
5. Le service parse all_task
6. Le service charge tous les user_id
7. Le repository insere une tache par user_id
8. La ligne summary_task passe en processed
9. En cas d'erreur de format, la ligne passe en failed
```

## Transactions et concurrence

Pour eviter deux watchers qui traitent la meme ligne :

- utiliser une transaction courte pour reclamer les lignes ;
- passer leur statut de `pending` a `processing` ;
- si possible, utiliser `SELECT ... FOR UPDATE SKIP LOCKED` avec MySQL 8 ;
- garder une contrainte unique `(user_id, source_summary_task_id)`.

La contrainte unique est importante car elle protege contre les doublons meme
si le process crash entre l'insertion des taches et le passage en `processed`.

Il faut aussi gerer les lignes bloquees en `processing` trop longtemps :

```text
processing_started_at < now - timeout
```

Ces lignes peuvent etre remises en `pending` par le watcher au debut d'une
iteration.

## Comportement en cas d'erreur

### Format invalide

Exemples invalides :

```text
""
"description sans separateur"
" || description sans nom"
```

Action :

- ne pas creer de taches ;
- marquer la ligne `failed` ;
- stocker une erreur courte dans `processing_error` ;
- logger l'incident.

### Aucun utilisateur en base

Action recommandee :

- marquer la ligne `processed` ;
- creer 0 tache ;
- logger `0 users found`.

Cela respecte la regle "creer pour tous les users existants" : s'il n'y en a
aucun, il n'y a rien a creer.

### Erreur DB temporaire

Action :

- rollback de la session ;
- laisser la ligne en `pending` ou remettre en `pending` via le timeout ;
- le watcher reessaie au tour suivant.

## Lancement en production

Mode recommande : un service separe.

Exemple Docker Compose :

```yaml
services:
  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

  summary-task-watcher:
    build: .
    command: python -m app.workers.summary_task_watcher
    depends_on:
      - db
```

Avec systemd ou Supervisor, l'idee est la meme : un process `api`, un process
`summary-task-watcher`.

## Pourquoi pas uniquement dans FastAPI ?

On peut techniquement demarrer une boucle dans `lifespan`, mais ce choix devient
risque avec :

- `uvicorn --workers 4`, car chaque worker peut lancer un watcher ;
- les redemarrages automatiques ;
- les tests HTTP ;
- le besoin de scaler l'API independamment du traitement asynchrone.

Si on le fait quand meme pour le developpement, il faut un flag :

```env
ENABLE_SUMMARY_TASK_WATCHER_IN_API=true
```

et le laisser a `false` en production.

## Tests a ajouter

Tests unitaires :

- `parse_summary_task_text("afjp || klehfahg")` retourne `("afjp", "klehfahg")` ;
- le parser trim les espaces ;
- le parser echoue si `||` est absent ;
- le parser echoue si le nom est vide.

Tests service :

- une ligne pending cree une tache pour chaque user ;
- les taches ont `Priority.MEDIUM` ;
- `start_date` et `end_date` sont remplies ;
- la ligne passe en `processed` ;
- une ligne invalide passe en `failed` ;
- relancer le traitement ne cree pas de doublons.

Tests integration :

- plusieurs lignes pending sont traitees par batch ;
- deux watchers concurrents ne creent pas de doublons ;
- une ligne bloquee en `processing` trop longtemps est reprise.

## Etapes d'implementation

1. Ajouter les champs de statut dans `SummaryTask`.
2. Ajouter `source_summary_task_id` et la contrainte unique dans `Task`.
3. Ajouter une migration Alembic ou, pour le cours/local, documenter le SQL
   `ALTER TABLE`.
4. Ajouter les methodes repository pour reclamer, traiter et marquer les lignes.
5. Ajouter `SummaryTaskProcessorService`.
6. Ajouter `app/workers/summary_task_watcher.py`.
7. Ajouter la configuration dans `Settings`.
8. Ajouter les tests unitaires et service.
9. Lancer le watcher comme process separe.

## Alternative plus scalable

Le polling toutes les 2 secondes est acceptable pour ce projet et reste simple
a comprendre. Pour une application plus grosse, la version production robuste
serait :

- creation d'une ligne `summary_task` ;
- publication d'un evenement dans une queue ;
- worker Celery/RQ/Arq qui consomme l'evenement ;
- retry/backoff gere par la queue ;
- monitoring dedie.

Mais pour garder l'architecture actuelle presque intacte, le watcher DB avec
etat persistant, idempotence et service separe est le meilleur compromis.
