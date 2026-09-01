from rest_framework import viewsets

from .models import Task
from .serializers import TaskSerializer
from .tasks import send_task_created_notification


class TaskViewSet(viewsets.ModelViewSet):
    """
    Full CRUD API for Task objects:
    GET/POST     /api/tasks/
    GET/PUT/PATCH/DELETE /api/tasks/{id}/
    """

    queryset = Task.objects.all()
    serializer_class = TaskSerializer

    def perform_create(self, serializer):
        task = serializer.save()
        # Fire the Celery task asynchronously — the API responds
        # immediately without waiting for the "notification" to send.
        send_task_created_notification.delay(task.id, task.title)
