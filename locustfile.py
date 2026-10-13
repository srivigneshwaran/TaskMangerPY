import random
from locust import HttpUser, between, task


class TaskManagerUser(HttpUser):
    """
    Simulates user interactions to benchmark API throughput and latency.
    Run with: locust -f locustfile.py --host=http://127.0.0.1:8000
    """

    wait_time = between(0.1, 0.5)

    @task(3)
    def list_tasks(self):
        """Test GET /api/tasks/ endpoint."""
        self.client.get("/api/tasks/")

    @task(2)
    def create_task(self):
        """Test POST /api/tasks/ endpoint (triggers Celery background job)."""
        payload = {
            "title": f"Load Test Task #{random.randint(1000, 9999)}",
            "description": "Benchmarking asynchronous task creation",
        }
        self.client.post("/api/tasks/", json=payload)
