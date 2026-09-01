import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "taskmanager.settings")

app = Celery("taskmanager")

# Read CELERY_* settings from Django's settings.py, using a "CELERY_" prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks.py in each installed app (e.g. tasks/tasks.py).
app.autodiscover_tasks()
