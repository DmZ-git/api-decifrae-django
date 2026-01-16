# 🎵 DECIFRAÊ - Conversor de Áudio para Cifras

Sistema completo para conversão automática de arquivos de áudio em cifras musicais usando IA.

## 📁 Estrutura do Projeto

```
Decifrae-main1/
├── api/                    # Backend Django REST API
│   ├── core/              # Configurações Django
│   ├── migrations/        # Migrações do banco
│   ├── models.py         # Modelos de dados
│   ├── views.py          # Endpoints da API
│   ├── serializers.py    # Serializers REST
│   ├── middleware.py     # Middleware de autenticação
│   └── supabase_client.py # Cliente Supabase
│
├── frontend/              # Frontend React + Vite
│   ├── src/
│   │   ├── components/   # Componentes React
│   │   ├── pages/        # Páginas
│   │   ├── lib/          # Utilitários (api-client, supabase)
│   │   └── contexts/     # React Contexts (Auth)
│   ├── public/           # Arquivos estáticos
│   └── package.json      # Dependências npm
│
├── .env                   # Variáveis de ambiente (Backend)
├── manage.py             # Django management
├── requirements.txt      # Dependências Python
└── README.md            # Este arquivo
```

## 🚀 Como Rodar

### 1. Backend (API Django)

```bash
# Instalar dependências Python
pip install -r requirements.txt

# Criar/aplicar migrações
python manage.py migrate

# Iniciar servidor
python manage.py runserver
```

**Servidor:** http://localhost:8000
**API:** http://localhost:8000/api/

### 2. Frontend (React)

```bash
# Navegar para o frontend
cd frontend

# Instalar dependências
npm install

# Iniciar servidor de desenvolvimento
npm run dev
```

**Servidor:** http://localhost:8080

## 🔑 Configuração

### 1. Variáveis de Ambiente

#### Backend (.env na raiz)
```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,*

# Supabase
SUPABASE_URL=https://jttksxgmlaztmeiomtfo.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
SUPABASE_STORAGE_BUCKET=audio-files

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:8080,http://127.0.0.1:8080
```

#### Frontend (frontend/.env)
```env
VITE_API_URL=http://localhost:8000/api
VITE_SUPABASE_URL=https://jttksxgmlaztmeiomtfo.supabase.co
VITE_SUPABASE_ANON_KEY=your_anon_key
```

## 🎯 Funcionalidades

### ✅ Implementado
- 🔐 Sistema de autenticação (Email/Password + Google OAuth)
- 📤 Upload de arquivos de áudio
- 💾 Armazenamento no Supabase Storage
- 🗄️ API REST completa (CRUD)
- 🎨 Interface moderna com React + shadcn/ui
- 📱 Design responsivo

### 🚧 Em Desenvolvimento
- 🎵 Extração automática de cifras
- 📊 Visualização de cifras
- 📝 Editor de cifras
- 🎼 Sistema de playlists
- 📥 Download de cifras em PDF

## 📡 Endpoints da API

### Autenticação
- Gerenciada pelo Supabase Auth no frontend
- Middleware valida tokens JWT nas requisições

### Áudio
- `GET /api/audio/` - Lista arquivos
- `POST /api/audio/` - Upload de arquivo
- `GET /api/audio/{id}/` - Detalhes
- `DELETE /api/audio/{id}/` - Deletar

### Cifras
- `GET /api/transcriptions/` - Lista cifras
- `POST /api/transcriptions/` - Criar cifra
- `GET /api/transcriptions/{id}/` - Detalhes
- `PATCH /api/transcriptions/{id}/` - Atualizar
- `DELETE /api/transcriptions/{id}/` - Deletar

### Playlists
- `GET /api/playlists/` - Lista playlists
- `POST /api/playlists/` - Criar playlist
- `POST /api/playlists/{id}/add_transcription/` - Adicionar cifra
- `POST /api/playlists/{id}/remove_transcription/` - Remover cifra

## 🛠️ Stack Tecnológica

### Backend
- **Python 3.13** - Linguagem
- **Django 6.0** - Framework web
- **Django REST Framework** - API REST
- **Supabase** - Storage + Auth
- **PostgreSQL/SQLite** - Banco de dados

### Frontend
- **React 18** - Biblioteca UI
- **TypeScript** - Tipagem estática
- **Vite** - Build tool
- **shadcn/ui** - Componentes UI
- **Tailwind CSS** - Estilização
- **Supabase JS** - Cliente Supabase

## 🔄 Fluxo de Integração

```
┌─────────────┐     ┌───────────────┐     ┌──────────────┐
│  Frontend   │────▶│  Django API   │────▶│  Supabase    │
│  (React)    │     │  (REST)       │     │  (Storage)   │
│  :8080      │     │  :8000        │     │              │
└─────────────┘     └───────────────┘     └──────────────┘
      │                     │                      │
      │  1. Login (JWT)     │                      │
      │────────────────────▶│                      │
      │                     │  2. Validate Token   │
      │                     │─────────────────────▶│
      │  3. Upload Audio    │                      │
      │────────────────────▶│                      │
      │                     │  4. Store File       │
      │                     │─────────────────────▶│
      │  5. Return URL      │                      │
      │◀────────────────────│                      │
```

## 📝 Desenvolvimento

### Estrutura de Commits
- `feat:` - Nova funcionalidade
- `fix:` - Correção de bug
- `docs:` - Documentação
- `style:` - Formatação
- `refactor:` - Refatoração
- `test:` - Testes

### Padrões de Código
- **Backend:** PEP 8 (Python)
- **Frontend:** ESLint + Prettier

## 🐛 Troubleshooting

### Backend não inicia
```bash
# Verificar dependências
pip install -r requirements.txt

# Verificar migrações
python manage.py migrate

# Verificar .env
cat .env
```

### Frontend não inicia
```bash
# Limpar node_modules
rm -rf node_modules package-lock.json
npm install

# Verificar .env
cat frontend/.env
```

### Erro de CORS
- Confirme que o backend está rodando
- Verifique `CORS_ALLOWED_ORIGINS` no settings.py

### Erro de Upload
- Verifique credenciais do Supabase
- Confirme permissões do bucket `audio-files`

## 📄 Licença

Projeto educacional - Livre para uso e modificação

## 👥 Contribuidores

- Desenvolvedor Principal: [Seu Nome]

## 📞 Suporte

Para dúvidas e suporte:
- Abra uma issue no repositório
- Email: suporte@decifrae.com
