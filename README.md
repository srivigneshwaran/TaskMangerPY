# Task Manager API

A small backend project built to practice the exact stack used at Cuculus
(Junior Python Developer role): **Python, Django, Django REST Framework,
Celery, Redis, Docker, and SQL (PostgreSQL)**.

It's a simple Task/To-Do REST API. When a task is created, the API responds
immediately, and a Celery background worker asynchronously logs a
"notification" — demonstrating the request/response cycle staying fast while
slower work happens off the main thread.

## Stack

- **Django** — web framework, ORM, admin site
- **Django REST Framework (DRF)** — REST API (ModelViewSet + router)
- **Celery** — async/background task processing
- **Redis** — Celery message broker + result backend
- **PostgreSQL** (via Docker) / **SQLite** (for quick local runs without Docker)
- **Docker & docker-compose** — containerized services (web, worker, db, redis)

## Project structure

```
taskmanager/
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── taskmanager/          # project settings, urls, celery app
│   ├── settings.py
│   ├── urls.py
│   └── celery.py
└── tasks/                # the app
    ├── models.py         # Task model
    ├── serializers.py    # DRF serializer
    ├── views.py          # DRF ModelViewSet
    ├── urls.py           # DRF router
    ├── tasks.py          # Celery task (async notification)
    └── admin.py          # Django admin registration
```

## API

| Method | Endpoint            | Description        |
|--------|----------------------|---------------------|
| GET    | `/api/tasks/`         | List all tasks      |
| POST   | `/api/tasks/`         | Create a task        |
| GET    | `/api/tasks/{id}/`    | Retrieve a task      |
| PATCH  | `/api/tasks/{id}/`    | Partially update      |
| PUT    | `/api/tasks/{id}/`    | Full update           |
| DELETE | `/api/tasks/{id}/`    | Delete a task          |

Example:
```bash
curl -X POST http://127.0.0.1:8000/api/tasks/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Learn Django", "description": "Build a REST API"}'
```

Creating a task triggers `send_task_created_notification.delay(...)`, which
runs asynchronously on the Celery worker and logs a notification message —
check the worker's terminal output to see it fire.

## Running locally (no Docker)

Uses SQLite automatically if no `POSTGRES_DB` env var is set.

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py runserver      # terminal 1

# Requires a local Redis server running on localhost:6379
celery -A taskmanager worker --loglevel=info   # terminal 2
```

## Running with Docker (Postgres + Redis + web + worker)

```bash
docker-compose up --build
```

This starts four containers: `db` (Postgres), `redis`, `web` (Django +
Gunicorn), and `worker` (Celery). The API is available at
`http://localhost:8000/api/tasks/`.

## What this project is for

Built while preparing for a Junior Python Developer role, to get hands-on
with Django, DRF, Celery, Redis, and Docker beyond just reading docs —
CRUD endpoints, async task processing, and containerized multi-service
setup, end to end.
