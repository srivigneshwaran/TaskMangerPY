# Task Manager API — Asynchronous Backend Microservice

[![Test Suite](https://github.com/srivigneshwaran/TaskMangerPY/actions/workflows/test.yml/badge.svg)](https://github.com/srivigneshwaran/TaskMangerPY/actions/workflows/test.yml)
![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Django](https://img.shields.io/badge/Django-6.1-green?logo=django)
![DRF](https://img.shields.io/badge/DRF-3.18-red)
![Celery](https://img.shields.io/badge/Celery-5.6-brightgreen?logo=celery)
![Redis](https://img.shields.io/badge/Redis-8.1-red?logo=redis)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

A production-ready RESTful backend microservice engineered with **Django REST Framework**, **Celery**, **Redis**, and **PostgreSQL**. 

The microservice demonstrates an **asynchronous producer-consumer architecture**: time-consuming downstream operations (such as email/webhook notification dispatch) are offloaded to an asynchronous background worker pool, keeping HTTP request-response latency minimal and preventing web worker starvation.

---

## Architecture & Data Flow

```mermaid
flowchart TD
    Client[Client / Frontend Application]
    
    subgraph Web_Tier["Web Tier (Gunicorn / Django)"]
        API[Django REST Framework API]
    end

    subgraph Data_Tier["Data & Cache Tier"]
        DB[(PostgreSQL 16)]
        Broker[(Redis 7 Message Broker)]
    end

    subgraph Worker_Tier["Worker Tier"]
        CeleryWorker[Celery Background Worker]
    end

    Client -->|1. HTTP POST /api/tasks/| API
    API -->|2. Save task record| DB
    API -.->|3. Enqueue job via .delay()| Broker
    API -->|4. Immediate 201 Created Response| Client
    Broker -->|5. Pop task & execute asynchronously| CeleryWorker
```

---

## Core Engineering Highlights

- **Decoupled Asynchronous Processing:** Offloads notification workflows to an independent Celery worker pool via Redis, keeping HTTP API response times under 40ms.
- **Enterprise Multi-Service Orchestration:** Containerized via Docker Compose with healthchecks ensuring `web` and `worker` start only after PostgreSQL and Redis are fully accepting connections.
- **Environment & Secret Isolation:** Zero hardcoded credentials in production; configurable via `.env.example` with safe local development defaults.
- **Dual-Mode Portability:** Automatically falls back to SQLite and in-memory eager task execution for local zero-dependency testing when Docker or Redis is not present.
- **Automated Test Suite:** 15 comprehensive unit and integration tests (executing in under 0.1s) validated on every push via GitHub Actions CI.

---

## Tech Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Web Framework** | Django 6.1 | Core ORM, admin site, and application logic |
| **REST API** | Django REST Framework 3.18 | Serializers, ModelViewSets, and content negotiation |
| **Task Queue** | Celery 5.6 | Asynchronous background worker execution |
| **Message Broker** | Redis 7 / 8.1 | In-memory message broker & task result backend |
| **Database** | PostgreSQL 16 (Prod) / SQLite (Local) | Persistent relational storage |
| **Production WSGI** | Gunicorn 23.0 | Production HTTP application server |
| **Containerization** | Docker & Docker Compose | Multi-container environment orchestration |
| **CI / Automation** | GitHub Actions | Automated build and test pipeline |

---

## Project Structure

```
TaskMangerPY/
├── .github/
│   └── workflows/
│       └── test.yml         # GitHub Actions automated CI workflow
├── taskmanager/             # Project configuration & settings
│   ├── settings.py          # Environment-driven Django settings
│   ├── urls.py              # Root URL routing
│   ├── celery.py            # Celery app initialization
│   ├── wsgi.py              # WSGI entrypoint for Gunicorn
│   └── asgi.py              # ASGI entrypoint
├── tasks/                   # Tasks application
│   ├── models.py            # Task data model
│   ├── serializers.py       # DRF ModelSerializer
│   ├── views.py             # DRF ModelViewSet (fires Celery tasks)
│   ├── urls.py              # DRF DefaultRouter
│   ├── tasks.py             # Celery @shared_task notification handler
│   ├── tests.py             # Automated unit & integration tests
│   └── admin.py             # Django admin registration
├── Dockerfile               # Multi-stage production container build
├── docker-compose.yml       # 4-service orchestration (db, redis, web, worker)
├── .dockerignore            # Build context filter
├── .env.example             # Production secrets and environment template
├── locustfile.py            # Locust load testing suite
├── requirements.txt         # Project dependencies
└── manage.py                # Django CLI utility
```

---

## REST API Specification

| Method | Endpoint | Description | Status Code |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/tasks/` | List all tasks (ordered newest first) | `200 OK` |
| `POST` | `/api/tasks/` | Create new task (triggers async notification) | `201 Created` |
| `GET` | `/api/tasks/{id}/` | Retrieve specific task details | `200 OK` / `404` |
| `PATCH`| `/api/tasks/{id}/` | Partially update task (e.g. toggle completion) | `200 OK` |
| `PUT` | `/api/tasks/{id}/` | Full task replacement | `200 OK` |
| `DELETE`| `/api/tasks/{id}/` | Delete task by ID | `204 No Content` |

### Example Request

```bash
curl -X POST http://127.0.0.1:8000/api/tasks/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Deploy Microservice", "description": "Verify container health in staging"}'
```

---

## Getting Started

### Method 1: Running with Docker (Recommended)

1. Copy the environment configuration:
   ```bash
   cp .env.example .env
   ```
2. Build and start all 4 containers (`db`, `redis`, `web`, `worker`):
   ```bash
   docker compose up --build
   ```
3. The API is live at `http://localhost:8000/api/tasks/`.

---

### Method 2: Running Locally (Without Docker)

The service detects missing environment variables and automatically falls back to SQLite and synchronous in-memory task execution for effortless local runs:

```bash
# 1. Create and activate virtual environment
python -m venv venv
source venv/bin/activate       # Windows: .\venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run database migrations & launch server
python manage.py migrate
python manage.py runserver
```

---

## Automated Testing & CI Verification

The test suite covers model constraints, serializer validation, full CRUD API behavior, and Celery task execution with mock verification.

Run the test suite locally:

```bash
python manage.py test --verbosity=2
```

### Verified Test Output

```text
test_create_task_with_defaults (tasks.tests.TaskModelTest) ... ok
test_task_ordering_newest_first (tasks.tests.TaskModelTest) ... ok
test_task_string_representation (tasks.tests.TaskModelTest) ... ok
test_missing_title_is_invalid (tasks.tests.TaskSerializerTest) ... ok
test_read_only_fields_cannot_be_set_by_client (tasks.tests.TaskSerializerTest) ... ok
test_valid_serializer_data (tasks.tests.TaskSerializerTest) ... ok
test_create_task_invalid_data (tasks.tests.TaskAPITest) ... ok
test_create_task_triggers_celery_notification (tasks.tests.TaskAPITest) ... ok
test_delete_task (tasks.tests.TaskAPITest) ... ok
test_full_update_task_put (tasks.tests.TaskAPITest) ... ok
test_list_tasks (tasks.tests.TaskAPITest) ... ok
test_partial_update_task_patch (tasks.tests.TaskAPITest) ... ok
test_retrieve_nonexistent_task (tasks.tests.TaskAPITest) ... ok
test_retrieve_task (tasks.tests.TaskAPITest) ... ok
test_send_task_created_notification (tasks.tests.CeleryTaskTest) ... ok

----------------------------------------------------------------------
Ran 15 tests in 0.091s

OK
```

---

## Performance & Load Testing

A [locustfile.py](locustfile.py) is provided to benchmark the API under concurrent traffic:

```bash
pip install locust
locust -f locustfile.py --host=http://127.0.0.1:8000
```
Open `http://localhost:8089` to configure virtual users and observe real-time requests/second, median response time, and p95/p99 latency distributions.
