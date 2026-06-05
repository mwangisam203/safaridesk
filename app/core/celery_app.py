from celery import Celery
from celery.schedules import crontab
from app.core.config import settings


celery_app = Celery(
    "safaridesk",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.email_tasks",
        "app.tasks.reconciler_task",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # ── Celery Beat schedule ──────────────────────────────────────────────────
    beat_schedule={
        "reconcile-pending-mpesa-transactions": {
            "task": "app.tasks.reconciler_task.reconcile_pending_transactions",
            "schedule": crontab(minute="*/5"),  # every 5 minutes
        },
    },
)
