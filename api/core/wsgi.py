import os
import logging
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.core.settings')
application = get_wsgi_application()

try:
    from django.conf import settings
    db = settings.DATABASES.get('default', {})
    engine = db.get('ENGINE')
    name = db.get('NAME') or db.get('HOST')
    logging.getLogger(__name__).info(f"DB engine: {engine} | target: {name}")
except Exception:
    pass
