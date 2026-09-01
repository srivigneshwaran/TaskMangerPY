import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def send_task_created_notification(task_id: int, title: str) -> str:
    """
    Simulates sending a notification (e.g. email/Slack message) when a
    new Task is created. Runs asynchronously via a Celery worker so the
    API request that created the Task doesn't have to wait for it.
    """
    message = f"[notification] Task #{task_id} '{title}' was created."
    logger.info(message)
    return message
