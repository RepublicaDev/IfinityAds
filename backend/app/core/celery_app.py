import os
from celery import Celery

REDIS_URL = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"

celery_app = Celery(
    "infinityad",
    broker=REDIS_URL,
    backend=os.getenv("CELERY_RESULT_BACKEND") or REDIS_URL,
)

# Configurações mínimas recomendadas
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
