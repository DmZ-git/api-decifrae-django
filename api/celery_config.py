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

# Configurações de otimização para ambiente com pouca memória (Render Free Tier)
app.conf.update(
    # Workers - Otimizado para 512MB RAM
    CELERYD_MAX_TASKS_PER_CHILD=10,  # Reinicia após 10 tasks (libera memória acumulada)
    CELERYD_POOL='solo',  # Solo pool usa menos memória que prefork
    CELERYD_MAX_MEMORY_PER_CHILD=400000,  # 400MB max (deixa margem para o SO)
    
    # Task defaults - Limites para processamento de áudio
    CELERY_TASK_SOFT_TIME_LIMIT=300,  # 5 min soft limit
    CELERY_TASK_TIME_LIMIT=360,  # 6 min hard limit
    CELERY_TASK_TRACK_STARTED=True,
    CELERY_TASK_ACKS_LATE=True,  # Confirma apenas após completar (evita perda)
    CELERY_WORKER_PREFETCH_MULTIPLIER=1,  # Pega 1 task por vez (não acumula)
    CELERY_WORKER_MAX_TASKS_PER_CHILD=10,  # Redundante mas garante
    
    # Result backend
    CELERY_RESULT_BACKEND='redis://localhost:6379/0',
    CELERY_BROKER_URL='redis://localhost:6379/0',
    CELERY_RESULT_EXPIRES=3600,  # Expira resultados após 1h (economiza Redis)
    
    # Serialization
    CELERY_ACCEPT_CONTENT=['json'],
    CELERY_TASK_SERIALIZER='json',
    CELERY_RESULT_SERIALIZER='json',
    
    # Performance e confiabilidade
    CELERY_TASK_REJECT_ON_WORKER_LOST=True,  # Re-enfileira se worker morrer
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP=True,
    CELERY_BROKER_TRANSPORT_OPTIONS={
        'visibility_timeout': 3600,  # 1 hora de timeout
        'max_connections': 2,  # Limita conexões Redis
    },
)

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
