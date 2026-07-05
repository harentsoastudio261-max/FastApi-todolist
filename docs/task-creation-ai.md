# Task creation avec IA

Ce document explique comment ajouter proprement une nouvelle fonctionnalite :

```http
POST /task_creation
```

Endpoint protege qui recoit :

```json
{
  "type": "hobbies"
}
```

ou :

```json
{
  "type": "work"
}
```

Le backend utilise ensuite une IA pour generer un `name` et une `description`,
puis sauvegarde la tache dans `tasks` pour l'utilisateur connecte.

## Objectif

Le endpoint doit :

1. verifier l'utilisateur courant ;
2. recevoir un type de creation : `hobbies` ou `work` ;
3. appeler le service adapte au type ;
4. demander a une IA de proposer une tache ;
5. sauvegarder la tache en base ;
6. retourner la tache creee.

## Decision d'architecture

On garde l'architecture actuelle :

```text
HTTP request
  -> router
  -> controller
  -> manager
  -> use case
  -> service
  -> provider IA
  -> repository
  -> model
```

Le point important : Gemini ne doit pas etre appele directement depuis le
router, le controller ou le repository.

On ajoute une couche `providers` pour isoler l'IA :

```text
app/providers/ai/
  __init__.py
  base.py
  gemini_task_provider.py
```

Comme ca, si plus tard on remplace Gemini par OpenAI, Anthropic, un model local
ou un fake provider pour les tests, on change surtout le provider et le wiring,
pas toute l'application.

On ajoute aussi une couche `use_cases` pour eviter qu'un service orchestre
d'autres services. Dans cette architecture, le manager assemble les objets, le
controller appelle un use case, et le use case choisit quel service specialise
utiliser.

```text
app/use_cases/
  __init__.py
  task_creation_use_case.py
```

## Dependances Gemini recommandees

La documentation officielle Gemini recommande le SDK Google GenAI pour Python :

```bash
pip install google-genai
```

Donc dans `requirements.txt`, ajouter :

```text
google-genai
```

Dependances deja presentes et utiles :

```text
pydantic
pydantic-settings
sqlalchemy
fastapi
```

Optionnel pour une version production plus robuste :

```text
tenacity
```

`tenacity` peut servir a faire des retries propres si l'appel IA echoue
temporairement. Ce n'est pas obligatoire pour une premiere version.

Sources officielles :

- Gemini recommande `google-genai` comme SDK officiel production-ready et donne `pip install google-genai` comme installation Python : https://ai.google.dev/gemini-api/docs/libraries
- Gemini recommande les variables d'environnement `GEMINI_API_KEY` ou `GOOGLE_API_KEY` pour les cles API : https://ai.google.dev/gemini-api/docs/api-key
- Gemini supporte les structured outputs avec schema JSON/Pydantic, utile pour forcer une reponse `{ "name": "...", "description": "..." }` : https://ai.google.dev/gemini-api/docs/structured-output

## Configuration

Ajouter dans `app/core/config.py` :

```python
gemini_api_key: str | None = None
gemini_model: str = "gemini-3.5-flash"
ai_provider: str = "gemini"
```

Ajouter dans `.env.example` :

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash
```

Note : le SDK Gemini peut lire `GEMINI_API_KEY` automatiquement. On peut aussi
passer explicitement la cle depuis `settings.gemini_api_key`.

## Schemas

Ajouter dans `app/schemas/__init__.py` :

```python
class TaskCreationType(str, enum.Enum):
    HOBBIES = "hobbies"
    WORK = "work"


class TaskCreationCreate(BaseModel):
    type: TaskCreationType


class GeneratedTaskIdea(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
```

`TaskCreationCreate` represente l'entree HTTP.

`GeneratedTaskIdea` represente la sortie attendue de l'IA. Elle ne doit pas etre
retournee directement si on veut retourner une vraie `TaskRead` apres
sauvegarde.

## Provider IA

### Interface

Fichier :

```text
app/providers/ai/base.py
```

Contenu propose :

```python
from typing import Protocol

from app.schemas import GeneratedTaskIdea, TaskCreationType


class TaskIdeaProvider(Protocol):
    def generate_task_idea(self, task_type: TaskCreationType) -> GeneratedTaskIdea:
        ...
```

Pourquoi une interface :

- le service metier depend d'un contrat, pas de Gemini ;
- les tests peuvent utiliser un fake provider ;
- changer d'IA ne force pas a modifier les controllers.

### Provider Gemini

Fichier :

```text
app/providers/ai/gemini_task_provider.py
```

Responsabilite :

- construire le prompt ;
- appeler Gemini ;
- demander une reponse structuree ;
- valider le resultat avec `GeneratedTaskIdea`.

Pseudo-code :

```python
from google import genai

from app.schemas import GeneratedTaskIdea, TaskCreationType


class GeminiTaskIdeaProvider:
    def __init__(self, api_key: str | None, model: str):
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()
        self.model = model

    def generate_task_idea(self, task_type: TaskCreationType) -> GeneratedTaskIdea:
        prompt = build_prompt(task_type)
        response = self.client.interactions.create(
            model=self.model,
            input=prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": GeneratedTaskIdea.model_json_schema(),
            },
        )
        return GeneratedTaskIdea.model_validate_json(response.output_text)
```

## Prompts

Le prompt doit etre petit, clair et oriente sortie JSON.

Pour `hobbies` :

```text
Generate one useful personal hobby task.
Return only JSON with:
- name: short task title, max 255 characters
- description: practical task description
The task must be concrete and doable today.
```

Pour `work` :

```text
Generate one useful professional work task.
Return only JSON with:
- name: short task title, max 255 characters
- description: practical task description
The task must be concrete, productive, and doable today.
```

Le type controle donc le contexte de generation, pas la structure de la reponse.

## Services

L'utilisateur souhaite deux services separes :

```text
app/services/hobbies_task_creation_service.py
app/services/work_task_creation_service.py
```

Chaque service :

- appelle le provider IA avec son type ;
- transforme la reponse IA en `Task` ;
- sauvegarde via le repository ;
- retourne `TaskRead`.

### Hobbies service

```python
class HobbiesTaskCreationService:
    def __init__(self, repo: TaskRepository, ai_provider: TaskIdeaProvider):
        self.repo = repo
        self.ai_provider = ai_provider

    def create(self, user_id: int) -> TaskRead:
        idea = self.ai_provider.generate_task_idea(TaskCreationType.HOBBIES)
        task = Task(
            user_id=user_id,
            name=idea.name,
            description=idea.description,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow(),
            priority=Priority.MEDIUM,
        )
        return task_to_read(self.repo.add(task))
```

### Work service

Meme structure, mais avec :

```python
TaskCreationType.WORK
```

## Use case d'orchestration

Pour eviter que le controller fasse un `if/else` metier, et pour eviter qu'un
service appelle un autre service, ajouter un use case d'orchestration :

```text
app/use_cases/task_creation_use_case.py
```

Responsabilite :

- recevoir `TaskCreationCreate` ;
- choisir le bon service selon `type` ;
- retourner la tache creee ;
- garder les services specialises independants les uns des autres.

Pseudo-code :

```python
class TaskCreationUseCase:
    def __init__(
        self,
        hobbies_service: HobbiesTaskCreationService,
        work_service: WorkTaskCreationService,
    ):
        self.hobbies_service = hobbies_service
        self.work_service = work_service

    def create_task(self, data: TaskCreationCreate, user_id: int) -> TaskRead:
        if data.type == TaskCreationType.HOBBIES:
            return self.hobbies_service.create(user_id)
        if data.type == TaskCreationType.WORK:
            return self.work_service.create(user_id)
        raise ValueError("Unsupported task creation type")
```

Le controller reste donc fin, et les services ne s'appellent pas entre eux.

Pourquoi ce choix :

- `services/` contient la logique metier specialisee ;
- `use_cases/` contient l'orchestration d'un scenario applicatif ;
- `manager` reste le seul endroit qui assemble les dependances ;
- le code est plus lisible quand plusieurs services participent a une meme
  fonctionnalite.

## Repository

Pas besoin d'un nouveau model SQL.

On peut reutiliser `TaskRepository.add(task)`.

Si on veut tracer que la tache vient de l'IA, ajouter plus tard dans `Task` :

```text
source = manual | summary_task | ai_task_creation
ai_provider = gemini
ai_model = gemini-3.5-flash
```

Mais pour ne pas trop changer l'architecture maintenant, la premiere version
peut simplement creer une tache normale.

## Manager

Le `ServiceManager` doit construire les services specialises et exposer le use case d'orchestration :

```python
@dataclass
class ServiceManager:
    user_service: UserService
    task_service: TaskService
    task_creation_use_case: TaskCreationUseCase
    db: Session
```

Dans `build_manager(db)` :

```python
task_repo = TaskRepository(db)
ai_provider = build_task_idea_provider(settings)
hobbies_service = HobbiesTaskCreationService(task_repo, ai_provider)
work_service = WorkTaskCreationService(task_repo, ai_provider)
task_creation_use_case = TaskCreationUseCase(hobbies_service, work_service)
```

Puis :

```python
return ServiceManager(
    user_service=...,
    task_service=...,
    task_creation_use_case=task_creation_use_case,
    db=db,
)
```

Le controller utilisera donc :

```python
self.manager.task_creation_use_case.create_task(data, user_id)
```

## Controller

Nouveau fichier recommande :

```text
app/controllers/task_creation_controller.py
```

Responsabilite :

- verifier que l'utilisateur est present ;
- appeler `manager.task_creation_use_case` ;
- ne pas connaitre Gemini ;
- ne pas construire de prompt ;
- ne pas sauvegarder directement.

Pseudo-code :

```python
class TaskCreationController:
    def __init__(self, manager: ServiceManager, current_user: User):
        self.manager = manager
        self.current_user = current_user

    def create_task(self, data: TaskCreationCreate) -> TaskRead:
        return self.manager.task_creation_use_case.create_task(
            data,
            self.current_user.id,
        )
```

## Router

Nouveau fichier recommande :

```text
app/routers/task_creation_router.py
```

Endpoint :

```python
router = APIRouter(prefix="/task_creation", tags=["task_creation"])


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task_creation(
    data: TaskCreationCreate,
    controller: TaskCreationController = Depends(_controller),
):
    return controller.create_task(data)
```

Protection :

```python
current_user: User = Depends(get_current_user)
```

Donc le endpoint est protege comme les tasks existantes.

Dans `app/main.py` :

```python
from app.routers.task_creation_router import router as task_creation_router

app.include_router(task_creation_router)
```

## Flux complet

```text
POST /task_creation
  -> task_creation_router
  -> TaskCreationController
  -> ServiceManager.task_creation_use_case
  -> TaskCreationUseCase
  -> HobbiesTaskCreationService ou WorkTaskCreationService
  -> TaskIdeaProvider
  -> GeminiTaskIdeaProvider
  -> TaskRepository.add()
  -> TaskRead
```

## Gestion d'erreurs

Cas a gerer :

- type inconnu : FastAPI/Pydantic renvoie une erreur 422 ;
- cle Gemini absente : erreur de configuration claire au demarrage ou au premier appel ;
- Gemini indisponible : erreur technique propre, loggee, sans sauvegarder de tache ;
- reponse IA invalide : validation Pydantic echoue, aucune tache creee ;
- timeout IA : retourner une erreur claire au client.

Idealement, ajouter une exception metier :

```python
class AIProviderException(AppException):
    ...
```

ou une exception technique mappee par les handlers existants.

## Tests a ajouter

Tests unitaires :

- `TaskCreationCreate` accepte `hobbies` et `work` ;
- `TaskCreationCreate` refuse un type inconnu ;
- `TaskCreationUseCase` route vers le bon service ;
- `HobbiesTaskCreationService` cree une tache avec un fake provider ;
- `WorkTaskCreationService` cree une tache avec un fake provider ;
- si le provider retourne une reponse invalide, aucune tache n'est sauvegardee.

Tests integration :

- `POST /task_creation` sans auth est refuse ;
- `POST /task_creation` avec auth cree une tache ;
- la tache creee appartient au user courant ;
- le repository est appele via le service, pas directement depuis le router.

## Etapes d'implementation

1. Ajouter `google-genai` dans `requirements.txt`.
2. Ajouter les variables Gemini dans `Settings` et `.env.example`.
3. Ajouter les schemas `TaskCreationType`, `TaskCreationCreate`, `GeneratedTaskIdea`.
4. Ajouter `app/providers/ai/base.py`.
5. Ajouter `app/providers/ai/gemini_task_provider.py`.
6. Ajouter une factory `build_task_idea_provider(settings)`.
7. Ajouter `HobbiesTaskCreationService`.
8. Ajouter `WorkTaskCreationService`.
9. Ajouter `TaskCreationUseCase` dans `app/use_cases/task_creation_use_case.py`.
10. Ajouter le use case dans `ServiceManager`.
11. Ajouter `TaskCreationController`.
12. Ajouter `TaskCreationRouter`.
13. Inclure le router dans `main.py`.
14. Ajouter les tests avec un fake provider.

## Pourquoi cette structure est maintenable

- Le router ne connait que HTTP.
- Le controller ne connait que l'utilisateur courant et le manager.
- Le use case orchestre le scenario applicatif.
- Les services portent la logique metier.
- Les services specialises ne s'appellent pas entre eux.
- Le repository reste responsable de la DB.
- Le provider IA est isole derriere une interface.
- Changer Gemini demande surtout de creer un nouveau provider et de changer la
  factory.

Exemple plus tard :

```text
GeminiTaskIdeaProvider
OpenAITaskIdeaProvider
LocalModelTaskIdeaProvider
FakeTaskIdeaProvider
```

Le reste du code continue de parler a `TaskIdeaProvider`.
