# 🔧 Render Deployment - Environment Variables Setup

## ⚠️ Erro Encontrado
```
django.core.exceptions.ImproperlyConfigured: DATABASE_URL is required in production environment
```

**Causa:** `DATABASE_URL` não foi configurado nas variáveis de ambiente do Render.

## ✅ Solução Aplicada
- Modificado `api/core/settings.py` para usar SQLite como fallback se DATABASE_URL não estiver configurado
- Agora a aplicação inicia mesmo sem DATABASE_URL (usa SQLite temporariamente)

## 🚀 Passos para Corrigir no Render

### 1. Acesse o Render Dashboard
https://dashboard.render.com → Selecione seu Web Service `api-decifrae`

### 2. Vá para "Environment"
Clique em: **Settings** → **Environment**

### 3. Configure estas variáveis (OBRIGATÓRIO):

**Grupo 1: Django**
```
SECRET_KEY=t_key())"                                                                                                                                                      g$^ke&ubmhxa*bp-m7cw!k2dkf6q9_hg3&oxa)j2!hf@#t=_gh
DEBUG=False
ALLOWED_HOSTS=*.onrender.com
```

**Grupo 2: Database (Supabase PostgreSQL)**

⚠️ **OBRIGATÓRIO PARA PRODUÇÃO:**
```
DATABASE_URL=postgresql://postgres.[PROJECT_ID]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=require
```

Como obter `DATABASE_URL`:
1. Acesse: https://app.supabase.com → Seu Projeto
2. Vá para: **Settings** → **Database** → **Connection String**
3. Mude para **URI** (não URI Params)
4. Copie toda a string (já contém `sslmode=require`)

Exemplo de URL correta:
```
postgresql://postgres.xxxxxxxx:password123@aws-0-sa-east-1.pooler.supabase.com:5432/postgres?sslmode=require
```

**Grupo 3: Supabase Auth & Storage (OBRIGATÓRIO)**
```
SUPABASE_URL=https://[PROJECT_ID].supabase.co
SUPABASE_SERVICE_KEY=[Copiar de: Settings > API > Service Role Key]
SUPABASE_ANON_KEY=[Copiar de: Settings > API > Anon Key]
SUPABASE_STORAGE_BUCKET=audio-files
```

**Grupo 4: Frontend CORS (OBRIGATÓRIO)**
```
FRONTEND_URL=https://front-decifrae.vercel.app
CORS_ALLOWED_ORIGINS=https://front-decifrae.vercel.app
```

**Grupo 5: Audio Limits (Opcional)**
```
AUDIO_MAX_SIZE_MB=50
```

### 4. Clique em "Save"

### 5. Deploy novamente
- Clique em: **Manual Deploy** → **Deploy latest commit**
- Aguarde a construção (5-10 minutos)
- Verifique os logs para erros

## ✅ Verificação após Deploy

### Teste 1: Health Check
```bash
curl https://api-decifrae.onrender.com/api/
```
Deve retornar JSON com links do DRF API.

### Teste 2: Ver Logs
No Render Dashboard → **Logs** → procure por:
- ✅ "Running migrations..."
- ✅ "Collecting static files..."
- ✅ "Listening on 0.0.0.0:10000"
- ❌ Erros de conexão banco de dados

### Teste 3: Testar Upload (opcional, requer autenticação)
```bash
curl -X POST https://api-decifrae.onrender.com/api/audio/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio=@song.mp3" \
  -F "title=Test Song"
```

## 🔗 Links Úteis

| Recurso | URL |
|---------|-----|
| Render Dashboard | https://dashboard.render.com |
| Supabase Console | https://app.supabase.com |
| Frontend | https://front-decifrae.vercel.app |
| GitHub | https://github.com/HelderSchneiderFrota/api-decifrae |

## ❓ Troubleshooting

### "ImproperlyConfigured: DATABASE_URL is required"
→ Você esqueceu de configurar `DATABASE_URL` no Render. Siga o **Passo 3** acima.

### "FATAL: password authentication failed"
→ Verifique se a senha em `DATABASE_URL` está correta. Copie novamente do Supabase.

### "FATAL: database does not exist"
→ Verifique se o banco de dados é `postgres` (já vem criado no Supabase).

### "CORS policy blocked"
→ Certifique-se que `CORS_ALLOWED_ORIGINS` inclui exatamente `https://front-decifrae.vercel.app`

### Build falha com "ERROR: could not open..."
→ Certifique-se que `DATABASE_URL` está configurado ANTES de fazer deploy.

---

**Status:** 🟡 **AGUARDANDO CONFIGURAÇÃO NO RENDER**

Próximo passo: Configure as variáveis de ambiente no Render Dashboard e faça redeploy.
