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
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
if os.environ.get('DATABASE_URL'):
    try:
        import dj_database_url
        DATABASES['default'] = dj_database_url.parse(os.environ.get('DATABASE_URL'))
    except Exception:
        pass
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'api', 'static')
AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'}, {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}, {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'}, {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_AUTHENTICATION_CLASSES': [],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
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
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Apenas em desenvolvimento

# Supabase Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY', '')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
SUPABASE_STORAGE_BUCKET = os.environ.get('SUPABASE_STORAGE_BUCKET', 'audio-files')

# Audio Processing Settings
AUDIO_MAX_SIZE_MB = int(os.environ.get('AUDIO_MAX_SIZE_MB', 50))

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
