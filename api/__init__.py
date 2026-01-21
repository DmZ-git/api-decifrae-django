# Import Celery app para auto-descobrir tasks
from .celery_config import app as celery_app

__all__ = ('celery_app',)

