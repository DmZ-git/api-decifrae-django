# API DECIFRAE

## Setup Local

\\\ash
pip install -r requirements.txt
python app.py migrate
python app.py runserver
\\\

Em outro terminal:
\\\ash
celery -A api worker -l info
\\\

## Deploy no Render.com

### 1. Preparar variáveis de ambiente
Copie \.env.example\ e configure com seus valores

### 2. Configure no Render Dashboard:
- **Build Command:** \ash build.sh\
- **Start Command:** \gunicorn api.core.wsgi\

### 3. Environment Variables no Render:
- SECRET_KEY (gere uma chave segura)
- DEBUG=False
- DATABASE_URL=postgresql://...
- CELERY_BROKER_URL=redis://...
- CORS_ALLOWED_ORIGINS=https://seu-frontend.com

### 4. Serviços necessários:
- PostgreSQL (Database)
- Redis (Celery Broker)
- Render Web Service (Django app)
- Render Background Worker (Celery)

## API Endpoints

- **POST** \/api/auth/signup/\ - Criar conta
- **POST** \/api/auth/login/\ - Fazer login
- **POST** \/api/auth/logout/\ - Fazer logout
- **GET** \/api/auth/me/\ - Dados do usuário
- **POST** \/api/audio/\ - Upload de áudio
- **GET** \/api/audio/\ - Listar áudios
- **POST** \/api/jobs/process_audio/\ - Processar áudio
- **GET** \/api/jobs/{id}/status/\ - Status de processamento
- **GET** \/api/transcriptions/\ - Listar cifras
- **GET** \/api/playlists/\ - Listar playlists
