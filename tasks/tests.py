from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Task
from .serializers import TaskSerializer
from .tasks import send_task_created_notification


class TaskModelTest(TestCase):
    """Unit tests for the Task model."""

    def test_create_task_with_defaults(self):
        task = Task.objects.create(title="Buy groceries")
        self.assertEqual(task.title, "Buy groceries")
        self.assertEqual(task.description, "")
        self.assertFalse(task.completed)
        self.assertIsNotNone(task.created_at)
        self.assertIsNotNone(task.updated_at)
        self.assertEqual(str(task), "Buy groceries")

    def test_task_string_representation(self):
        task = Task.objects.create(title="Learn Celery")
        self.assertEqual(str(task), "Learn Celery")

    def test_task_ordering_newest_first(self):
        first = Task.objects.create(title="First Task")
        second = Task.objects.create(title="Second Task")
        Task.objects.filter(pk=first.pk).update(
            created_at=timezone.now() - timedelta(hours=1)
        )
        Task.objects.filter(pk=second.pk).update(
            created_at=timezone.now()
        )
        tasks = list(Task.objects.all())
        self.assertEqual(tasks, [second, first])


class TaskSerializerTest(TestCase):
    """Unit tests for the TaskSerializer."""

    def test_valid_serializer_data(self):
        data = {
            "title": "Complete assignment",
            "description": "Finish Django unit tests",
            "completed": False,
        }
        serializer = TaskSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        task = serializer.save()
        self.assertEqual(task.title, "Complete assignment")
        self.assertEqual(task.description, "Finish Django unit tests")
        self.assertFalse(task.completed)

    def test_missing_title_is_invalid(self):
        data = {"description": "Missing title"}
        serializer = TaskSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("title", serializer.errors)

    def test_read_only_fields_cannot_be_set_by_client(self):
        data = {
            "title": "Immutable timestamp check",
            "id": 9999,
        }
        serializer = TaskSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        task = serializer.save()
        # id should be auto-assigned by the database, ignoring client-provided value
        self.assertNotEqual(task.id, 9999)


class TaskAPITest(APITestCase):
    """Integration tests for TaskViewSet endpoints."""

    def setUp(self):
        self.task1 = Task.objects.create(
            title="Task 1", description="Description 1", completed=False
        )
        self.task2 = Task.objects.create(
            title="Task 2", description="Description 2", completed=True
        )
        self.list_url = reverse("task-list")
        self.detail_url = reverse("task-detail", kwargs={"pk": self.task1.pk})

    def test_list_tasks(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    @patch("tasks.views.send_task_created_notification.delay")
    def test_create_task_triggers_celery_notification(self, mock_delay):
        payload = {"title": "Write documentation", "description": "Markdown guide"}
        response = self.client.post(self.list_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Write documentation")
        self.assertEqual(Task.objects.count(), 3)

        new_task = Task.objects.get(id=response.data["id"])
        mock_delay.assert_called_once_with(new_task.id, new_task.title)

    def test_create_task_invalid_data(self):
        response = self.client.post(self.list_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("title", response.data)

    def test_retrieve_task(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.task1.id)
        self.assertEqual(response.data["title"], "Task 1")

    def test_retrieve_nonexistent_task(self):
        url = reverse("task-detail", kwargs={"pk": 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_full_update_task_put(self):
        payload = {
            "title": "Task 1 Updated",
            "description": "Updated description",
            "completed": True,
        }
        response = self.client.put(self.detail_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task1.refresh_from_db()
        self.assertEqual(self.task1.title, "Task 1 Updated")
        self.assertTrue(self.task1.completed)

    def test_partial_update_task_patch(self):
        payload = {"completed": True}
        response = self.client.patch(self.detail_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task1.refresh_from_db()
        self.assertTrue(self.task1.completed)
        self.assertEqual(self.task1.title, "Task 1")

    def test_delete_task(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Task.objects.filter(pk=self.task1.pk).exists())


class CeleryTaskTest(TestCase):
    """Unit tests for the asynchronous Celery notification task."""

    def test_send_task_created_notification(self):
        with self.assertLogs("tasks.tasks", level="INFO") as log_context:
            result = send_task_created_notification(42, "Deploy to Staging")

        expected_msg = "[notification] Task #42 'Deploy to Staging' was created."
        self.assertEqual(result, expected_msg)
        self.assertTrue(
            any(expected_msg in record for record in log_context.output),
            "Expected notification log message not found in logger output.",
        )
