"""
Configuração do Celery para processamento assíncrono de áudio
"""
import os
from celery import Celery

# Configurar Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.core.settings')

app = Celery('api')

# Usar configurações do Django
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-descobrir tasks dos apps Django
app.autodiscover_tasks()

# Configurações de otimização
app.conf.update(
    # Workers
    CELERYD_MAX_TASKS_PER_CHILD=1000,  # Reinicia worker após 1000 tasks (limpa memória)
    CELERYD_POOL='solo',  # Em Render, usar solo (ou gevent se tiver gevent)
    
    # Task defaults
    CELERY_TASK_SOFT_TIME_LIMIT=600,  # 10 min soft limit
    CELERY_TASK_TIME_LIMIT=900,  # 15 min hard limit
    CELERY_TASK_TRACK_STARTED=True,
    CELERY_TASK_ACKS_LATE=True,
    CELERY_WORKER_PREFETCH_MULTIPLIER=1,
    
    # Result backend
    CELERY_RESULT_BACKEND='redis://localhost:6379/0',
    CELERY_BROKER_URL='redis://localhost:6379/0',
    
    # Serialization
    CELERY_ACCEPT_CONTENT=['json'],
    CELERY_TASK_SERIALIZER='json',
    CELERY_RESULT_SERIALIZER='json',
)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
