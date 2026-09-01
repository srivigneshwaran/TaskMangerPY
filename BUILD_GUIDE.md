# How This Project Was Built — Full Walkthrough

This document explains, step by step, what was built, how it was built, and
which technologies/frameworks were used — so you can genuinely explain this
project in an interview.

---

## 1. Goal

Build a small but real backend project using the exact stack listed in the
Cuculus Junior Python Developer job description:

- Python
- Django
- Django REST Framework (DRF)
- Celery (async/background tasks)
- Redis (Celery's message broker)
- SQL / PostgreSQL
- Docker

The project: a **Task Manager REST API** — create, read, update, and delete
tasks, with an async "notification" fired every time a task is created.

---

## 2. Technologies & What Each One Does

| Technology | Role in this project |
|---|---|
| **Python 3.12** | The language everything is written in. |
| **Django** | The web framework — handles URL routing, the ORM (database models), the admin site, and settings. |
| **Django REST Framework (DRF)** | Sits on top of Django to build REST APIs quickly — turns models into JSON, handles HTTP methods (GET/POST/PATCH/DELETE) automatically. |
| **Celery** | Runs slow/background work outside the main request-response cycle (e.g. sending a notification) so the API responds instantly. |
| **Redis** | The "message broker" Celery uses to pass task messages between the Django app and the Celery worker process. |
| **PostgreSQL** | The production-grade relational database (used when running via Docker). |
| **SQLite** | A lightweight file-based database used automatically for quick local testing without Docker. |
| **Docker / docker-compose** | Packages the whole app (web server, worker, database, Redis) into containers so it runs the same way on any machine. |
| **Gunicorn** | A production-ready WSGI server that runs the Django app inside Docker (Django's built-in `runserver` is dev-only). |

---

## 3. Step-by-Step: What We Actually Did

### Step 1 — Set up a Python virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install django djangorestframework celery redis
```
A virtual environment keeps this project's packages separate from the rest
of the system.

### Step 2 — Create the Django project and app
```bash
django-admin startproject taskmanager .
python manage.py startapp tasks
```
- `taskmanager/` = the project (global settings, URLs, Celery config)
- `tasks/` = the app (the actual Task feature: model, API, admin)

Django projects are usually split into small, focused "apps" like this.

### Step 3 — Define the data model (`tasks/models.py`)
```python
class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```
This is Django's **ORM** — instead of writing raw SQL to create a table, you
describe it as a Python class, and Django generates the SQL for you.

### Step 4 — Generate and run migrations
```bash
python manage.py makemigrations tasks
python manage.py migrate
```
- `makemigrations` reads the model and writes a migration file describing
  the SQL changes needed.
- `migrate` actually runs that SQL against the database, creating the
  `tasks_task` table.

### Step 5 — Build the REST API with DRF
Three files work together:

**`tasks/serializers.py`** — converts a `Task` object to/from JSON:
```python
class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "title", "description", "completed", "created_at", "updated_at"]
```

**`tasks/views.py`** — the API logic. `ModelViewSet` automatically gives you
list/create/retrieve/update/delete:
```python
class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
```

**`tasks/urls.py`** — wires the viewset to actual URLs using a DRF router:
```python
router = DefaultRouter()
router.register(r"tasks", TaskViewSet, basename="task")
```
This single router registration automatically creates all these routes:
`GET/POST /api/tasks/` and `GET/PUT/PATCH/DELETE /api/tasks/{id}/`.

### Step 6 — Add Celery for background/async processing
**`taskmanager/celery.py`** — creates the Celery application and tells it to
read settings from Django and auto-discover tasks:
```python
app = Celery("taskmanager")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

**`tasks/tasks.py`** — the actual background job, marked with `@shared_task`
so Celery knows it can run this asynchronously:
```python
@shared_task
def send_task_created_notification(task_id, title):
    logger.info(f"[notification] Task #{task_id} '{title}' was created.")
```

**Hooking it into the API** (`tasks/views.py`):
```python
def perform_create(self, serializer):
    task = serializer.save()
    send_task_created_notification.delay(task.id, task.title)
```
`.delay(...)` sends the job to Redis instantly and returns — it does **not**
wait for the notification to actually run. A separate Celery worker process
picks it up and runs it in the background. This is the core pattern behind
"the API responds fast, slow work happens elsewhere."

### Step 7 — Configure Redis + Celery settings (`taskmanager/settings.py`)
```python
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
```
Reading these from environment variables (instead of hardcoding) is what
lets the exact same code run both locally (`localhost:6379`) and inside
Docker (`redis:6379`, using the service name).

### Step 8 — Make the database configurable (Postgres or SQLite)
```python
if os.environ.get("POSTGRES_DB"):
    DATABASES = {"default": {"ENGINE": "django.db.backends.postgresql", ...}}
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", ...}}
```
No `POSTGRES_DB` env var → SQLite (fast local testing).
Running via `docker-compose` → Postgres (production-like).

### Step 9 — Register the model in Django Admin (`tasks/admin.py`)
```python
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "completed", "created_at")
```
Gives a free, ready-made admin UI at `/admin/` to view/edit tasks without
writing any HTML.

### Step 10 — Test it for real (not just written, actually run)
We ran three processes at once and confirmed they talk to each other:
```bash
redis-server --daemonize yes                          # message broker
python manage.py runserver 0.0.0.0:8000                # the API
celery -A taskmanager worker --loglevel=info           # background worker
```
Then exercised every endpoint with `curl`:
```bash
curl -X POST   http://127.0.0.1:8000/api/tasks/      -d '{"title": "Learn Django"}'
curl            http://127.0.0.1:8000/api/tasks/
curl -X PATCH  http://127.0.0.1:8000/api/tasks/1/    -d '{"completed": true}'
curl -X DELETE http://127.0.0.1:8000/api/tasks/1/
```
Result: `POST` returned the new task as JSON (`201 Created`), and the
Celery worker's terminal log showed the notification task being received
and completed **asynchronously**, milliseconds after the API had already
responded — proof the async pattern actually works, not just compiles.

### Step 11 — Containerize with Docker
**`Dockerfile`** — describes how to build an image containing Python, the
app code, and all dependencies, and runs it with Gunicorn (a real
production server, unlike Django's dev server).

**`docker-compose.yml`** — defines four services that run together:
- `db` — Postgres
- `redis` — Redis
- `web` — the Django app (Gunicorn)
- `worker` — the Celery worker

Running `docker-compose up --build` builds and starts all four containers,
networked together, so the whole system comes up with one command — this is
exactly how a real team would run (and deploy) this kind of service.

### Step 12 — Version control
```bash
git init
git add -A
git commit -m "Task Manager API: Django + DRF + Celery + Redis + Docker"
```
A clean, working first commit — ready to push to your own GitHub repo.

---

## 4. How to Talk About This in an Interview

If asked "walk me through a project," a natural way to describe it:

> "I built a small Task Manager REST API to get hands-on with Django, DRF,
> Celery, and Docker. It's basic CRUD for tasks, but the interesting part is
> that creating a task triggers a background Celery job — using Redis as
> the broker — so the API responds immediately instead of waiting on that
> extra work. I ran Django, Redis, and a Celery worker together locally and
> confirmed with curl that the async task actually fires. I also
> containerized the whole thing with Docker Compose — Postgres, Redis, the
> Django app, and the worker all running as separate services."

If asked a follow-up like "why Celery instead of just doing it directly in
the view?" — the honest answer: it decouples slow/unreliable work (like
sending an email or calling a third-party API) from the request-response
cycle, so a slow notification service can't make your API feel slow or
time out.

---

## 5. Files in This Project

```
taskmanager/
├── manage.py                  # Django's command-line utility
├── requirements.txt           # Python dependencies
├── Dockerfile                 # How to build the app's container image
├── docker-compose.yml         # How to run all 4 services together
├── README.md                  # Quick-start instructions
├── BUILD_GUIDE.md             # This file
├── taskmanager/                # Project-level config
│   ├── settings.py            # Django settings, DB config, Celery config
│   ├── urls.py                # Top-level URL routing
│   ├── celery.py              # Celery app setup
│   ├── wsgi.py / asgi.py      # Entry points for servers (Gunicorn uses wsgi.py)
└── tasks/                      # The Task feature (a Django "app")
    ├── models.py               # Task database model
    ├── serializers.py          # JSON <-> Task conversion (DRF)
    ├── views.py                 # API logic (DRF ModelViewSet)
    ├── urls.py                  # API routes (DRF router)
    ├── tasks.py                  # The Celery background task
    ├── admin.py                  # Django admin registration
    └── migrations/                # Auto-generated DB schema changes
```
