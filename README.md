# FastAPI TodoList — Reference Architecture

A layered, maintainable FastAPI project intended as a **template for larger, more complex Python projects**.

## Architecture (separation of concerns)

```
HTTP request
  -> router        (app/routers)        route definition + request/response wiring
  -> controller    (app/controllers)    request handling, status codes, no business logic
  -> service       (app/services)       business logic, validation rules
  -> repository    (app/repositories)   pure data access (SQLAlchemy), no HTTP awareness
  -> model         (app/models)         ORM entities + enums (persistence representation)
  -> schemas       (app/schemas)        Pydantic DTOs + REST<->model mappers
  -> manager       (app/managers)       coordinates one DB session + repos + services per request
  -> core          (app/core)           config, database, security, logging, exceptions
```

**Flow of dependencies:** router -> controller -> service -> repository -> model.
The `manager` builds the per-request object graph. Controllers depend only on the manager.

### Why each layer exists
- **router**: FastAPI's route table. Keeps path/method/schema concerns out of logic.
- **controller**: thin; maps use-case results to HTTP status codes.
- **service**: owns business rules (ownership checks, conflict detection, hashing).
- **repository**: owns queries. Swappable (Protocol-based) for testing.
- **schemas**: the **mapper** between REST payloads and ORM models (`task_to_read`, `task_create_to_model`, `apply_task_update`).
- **manager**: single dependency injected into controllers; makes the app testable end-to-end.

## Features
- JWT authentication stored in HttpOnly cookies, with CSRF protection for writes
- Per-user task CRUD with ownership enforcement
- Task attributes: `name`, `description`, `start_date`, `end_date`, `priority` (enum: low/medium/high)
- Validation: `end_date` must be after `start_date`; password >= 8 chars
- Structured logging (configurable level/format via env)
- Centralized HTTP + DB exception handling with consistent JSON error envelopes
- MySQL via SQLAlchemy + PyMySQL

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit DB credentials + JWT_SECRET
```

Create the MySQL database:
```sql
CREATE DATABASE todolist CHARACTER SET utf8mb4;
```
Tables are created automatically on startup (`Base.metadata.create_all`).

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Docs at `http://localhost:8000/docs`.

## API

| Method | Path                | Auth | Description          |
|--------|---------------------|------|----------------------|
| POST   | `/auth/register`    | no   | Register a user      |
| POST   | `/auth/login`       | no   | Start a cookie session |
| GET    | `/auth/csrf`        | no   | Bootstrap a CSRF token |
| GET    | `/tasks`            | yes  | List own tasks        |
| POST   | `/tasks`            | yes  | Create a task         |
| GET    | `/tasks/{id}`       | yes  | Get a task            |
| PUT    | `/tasks/{id}`       | yes  | Update a task         |
| DELETE | `/tasks/{id}`       | yes  | Delete a task         |
| GET    | `/health`           | no   | Health check          |

Auth is carried by HttpOnly cookies. Before every `POST`, `PUT`, `PATCH`, or `DELETE`, the frontend obtains `GET /auth/csrf` and sends the returned value in the `X-CSRF-Token` header. The backend compares that header with its matching HttpOnly CSRF cookie.

## Error envelope
All errors return:
```json
{ "error": { "code": "not_found", "message": "Task not found" } }
```

## Scaling this template
- Add a new resource by creating: model entity, schemas + mappers, repository, service, controller, router — then `include_router` in `main.py`.
- For complex domains, split services by aggregate and introduce a unit-of-work pattern around the manager.
- For async I/O, swap SQLAlchemy sync for `AsyncSession` and make repos/services `async`.
