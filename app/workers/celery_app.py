from celery import Celery

celery_app = Celery(
    "bts_pipeline",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_time_limit=3600 * 3,
)