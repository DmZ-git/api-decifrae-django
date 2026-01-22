from pathlib import Path
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-zq09*_713w)va0c-$d3o^km*-vl@5x1!4!3-81(su!%3oivl@k')
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')

# ALLOWED_HOSTS configuration
_allowed_hosts = ['localhost', '127.0.0.1']
if os.environ.get('RENDER_EXTERNAL_HOSTNAME'):
    _allowed_hosts.append(os.environ.get('RENDER_EXTERNAL_HOSTNAME'))
if os.environ.get('ALLOWED_HOSTS'):
    _allowed_hosts.extend([h.strip() for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h.strip()])
ALLOWED_HOSTS = _allowed_hosts
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'api.middleware.SupabaseAuthMiddleware',
]
ROOT_URLCONF = 'api.core.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'api' / 'templates'], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'api.core.wsgi.application'

# Database: prefer Supabase/Postgres via DATABASE_URL; fallback to SQLite
_database_url = os.environ.get('DATABASE_URL')

if _database_url:
    try:
        import dj_database_url
        # Supabase URL vem como postgresql://user:password@host:port/database
        # dj_database_url.parse() não requer URL encoding
        DATABASES = {
            'default': dj_database_url.config(
                default=_database_url,
                conn_max_age=600,
                ssl_require=True,
            )
        }
        # Ensure sslmode=require for psycopg
        if 'OPTIONS' not in DATABASES['default']:
            DATABASES['default']['OPTIONS'] = {}
        DATABASES['default']['OPTIONS']['sslmode'] = 'require'
    except Exception as e:
        import logging
        logging.warning(f"Failed to parse DATABASE_URL ({e}), falling back to SQLite")
        DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
else:
    # No DATABASE_URL: use SQLite (works for local dev or when DB not yet configured)
    import logging
    logging.warning("DATABASE_URL not set, using SQLite fallback. Set DATABASE_URL env var to use PostgreSQL/Supabase.")
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'}, {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}, {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'}, {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# CSRF Configuration
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'https://front-decifrae.vercel.app',  # Frontend em produção
    'https://api-decifrae.onrender.com',  # Backend em produção
]

# Adicionar origens dinâmicas do ambiente
if os.environ.get('FRONTEND_URL'):
    CSRF_TRUSTED_ORIGINS.append(os.environ.get('FRONTEND_URL'))
if os.environ.get('RENDER_EXTERNAL_URL'):
    CSRF_TRUSTED_ORIGINS.append(os.environ.get('RENDER_EXTERNAL_URL'))
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS Configuration
_cors_origins = [
    'http://localhost:3000',
    'http://127.0.0.1:3000',
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'https://front-decifrae.vercel.app',  # Frontend em produção
]

# Adicionar origens do ambiente
if os.environ.get('CORS_ALLOWED_ORIGINS'):
    _cors_origins.extend([o.strip() for o in os.environ.get('CORS_ALLOWED_ORIGINS').split(',') if o.strip()])

CORS_ALLOWED_ORIGINS = _cors_origins
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Supabase Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', 'audio-files')

# Audio Processing Settings
AUDIO_MAX_SIZE_MB = int(os.environ.get('AUDIO_MAX_SIZE_MB', 50))

# ===== CELERY CONFIGURATION (OTIMIZADO PARA RENDER FREE TIER 512MB) =====
# Em desenvolvimento, usar CELERY_ALWAYS_EAGER para modo síncrono
# Em produção, usar Redis do Render

if DEBUG:
    # Desenvolvimento: processar tasks sincronamente (sem Redis)
    CELERY_ALWAYS_EAGER = True
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'
else:
    # Produção: usar Redis do Render
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    CELERY_ALWAYS_EAGER = False
    
    # Produção: preferir Redis remoto, com fallback para DB
    broker_url = os.environ.get('CELERY_BROKER_URL', '')
    
    if broker_url:
        # Usar Redis remoto (Render)
        CELERY_BROKER_URL = broker_url
        CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', broker_url)
        CELERY_ALWAYS_EAGER = False
    else:
        # Fallback: usar banco de dados como broker (mais lento mas funciona sem Redis)
        CELERY_BROKER_URL = 'sqla+' + os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3')
        CELERY_RESULT_BACKEND = 'db+' + os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3')
        CELERY_ALWAYS_EAGER = False

# ===== CELERY CONFIGURATION (OTIMIZADO PARA RENDER FREE TIER 512MB) =====
# Estratégia:
# 1. DEBUG=True: EAGER mode (síncrono, sem Redis - desenvolvimento local)
# 2. DEBUG=False + CELERY_BROKER_URL: Redis remoto (Render com Redis)
# 3. DEBUG=False + sem CELERY_BROKER_URL: Database backend como broker (Render sem Redis)

if DEBUG:
    # Desenvolvimento: processar tasks sincronamente (sem Redis)
    CELERY_ALWAYS_EAGER = True
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
    CELERY_BROKER_URL = 'memory://'
    CELERY_RESULT_BACKEND = 'cache+memory://'
else:
    # Produção: preferir Redis remoto, com fallback para DB backend
    broker_url = os.environ.get('CELERY_BROKER_URL', '')
    
    if broker_url:
        # Usar Redis remoto (Render com serviço Redis)
        CELERY_BROKER_URL = broker_url
        CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', broker_url)
        CELERY_ALWAYS_EAGER = False
    else:
        # Fallback: usar banco de dados como broker
        # Isso funciona mesmo sem Redis, mas é mais lento
        try:
            db_url = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3')
            CELERY_BROKER_URL = 'sqla+' + db_url
            CELERY_RESULT_BACKEND = 'db+' + db_url
            CELERY_ALWAYS_EAGER = False
        except Exception:
            # Se ainda falhar, usar EAGER (sincronamente)
            CELERY_ALWAYS_EAGER = True
            CELERY_BROKER_URL = 'memory://'
            CELERY_RESULT_BACKEND = 'cache+memory://'
# Task defaults - Limites agressivos para processamento de áudio
# Task defaults - Limites agressivos para processamento de áudio
CELERY_TASK_SOFT_TIME_LIMIT = int(os.environ.get('CELERYD_TASK_SOFT_TIME_LIMIT', 300))  # 5 min
CELERY_TASK_TIME_LIMIT = int(os.environ.get('CELERYD_TASK_TIME_LIMIT', 360))  # 6 min
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # Pega 1 task por vez
CELERY_WORKER_MAX_TASKS_PER_CHILD = int(os.environ.get('CELERYD_MAX_TASKS_PER_CHILD', 10))  # Reinicia a cada 10 tasks

# Worker Settings - Otimizações de memória
CELERYD_POOL = 'solo'  # Solo pool = menos memória que prefork
CELERYD_MAX_MEMORY_PER_CHILD = 400000  # 400MB max (deixa margem no Free tier)
CELERYD_MAX_TASKS_PER_CHILD = 10

# Result Settings
CELERY_RESULT_EXPIRES = 3600  # 1 hora
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Broker Optimization
# Broker Optimization
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'visibility_timeout': 3600,  # 1 hora
    'max_connections': 2,  # Limita conexões
}
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True


# ===== MEMORY OPTIMIZATION =====
# Desabilita cache de librosa para economizar memória
os.environ['LIBROSA_CACHE_ENABLED'] = 'False'

# Configuração do ENVIRONMENT
ENVIRONMENT = 'production' if not DEBUG else 'development'

# Security Settings (Production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Proxy headers for Render
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
