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


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
