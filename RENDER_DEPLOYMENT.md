# Render Deployment Guide for API Decifrae

## ✅ Pre-Deployment Verification

All deployment files are ready:
- ✅ `render.yaml` — Configured with Python 3.13, gunicorn on port 10000
- ✅ `build.sh` — Runs migrations + static collection  
- ✅ `Procfile` — Single web process (Celery removed)
- ✅ `requirements.txt` — All dependencies pinned
- ✅ `.env.example` — Complete template for environment variables
- ✅ `api/models.py` — Django models mapped to Supabase table names
- ✅ `api/core/settings.py` — Production-ready with HTTPS + security headers

## 🚀 Step-by-Step Deployment

### 1. **Prepare GitHub**
```bash
cd C:\Users\Djmz2\Downloads\api-decifrae
git add -A
git commit -m "Production ready: Supabase table mapping, Render deployment config, Celery removed, tests passing"
git push origin main
```

### 2. **In Render Dashboard** → Create New → Web Service
- Connect GitHub repository: `api-decifrae`
- Choose Branch: `main`
- Build Command: *(auto-detected from `render.yaml`)*
- Start Command: *(auto-detected from `render.yaml`)*

### 3. **Set Environment Variables in Render**
Copy these into Render Dashboard (Settings → Environment):

```
# Django Core
SECRET_KEY=t_key())"                                                                                                                                                      g$^ke&ubmhxa*bp-m7cw!k2dkf6q9_hg3&oxa)j2!hf@#t=_gh
DEBUG=False
ALLOWED_HOSTS=*.onrender.com,api-decifrae.onrender.com

# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql://postgres.[SUPABASE_PROJECT_REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres?sslmode=require

# Supabase Auth & Storage
SUPABASE_URL=https://[PROJECT_REF].supabase.co
SUPABASE_SERVICE_KEY=[YOUR_SERVICE_ROLE_KEY]
SUPABASE_ANON_KEY=[YOUR_ANON_KEY]

# Frontend CORS
FRONTEND_URL=https://front-decifrae.vercel.app
CORS_ALLOWED_ORIGINS=https://front-decifrae.vercel.app

# Audio Upload Limits (MB)
MAX_AUDIO_SIZE_MB=50
```

### 4. **Get Supabase Credentials**
- Go to Supabase Dashboard → Settings → Database
  - Find `DATABASE_URL` (copy full connection string)
- Go to Supabase Dashboard → Settings → API
  - Copy `Service Role Key` (for `SUPABASE_SERVICE_KEY`)
  - Copy `Anon Key` (for `SUPABASE_ANON_KEY`)

### 5. **Deploy to Render**
1. Click **"Deploy"** in Render Dashboard
2. Wait for build (5-10 minutes)
3. Check build logs for errors:
   - Should see: `Running migrations...`
   - Should see: `Collecting static files...`
   - Should see: `Listening on 0.0.0.0:10000`

### 6. **Test Production Endpoints**
After deployment succeeds, test with `curl` or Postman:

**Health Check:**
```bash
curl https://api-decifrae.onrender.com/api/
```
Should return DRF root view (JSON).

**Upload Audio (if authenticated):**
```bash
curl -X POST https://api-decifrae.onrender.com/api/audio/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio=@test.mp3" \
  -F "title=Test Song"
```

## 🔍 Troubleshooting

### Build fails with "ModuleNotFoundError"
- Check `requirements.txt` has all dependencies
- Verify Python 3.13 compatibility

### Database connection error
- Verify `DATABASE_URL` has correct format
- Ensure Supabase PostgreSQL is accessible from Render
- Check credentials copied correctly

### Static files 404
- `build.sh` runs `collectstatic` during build
- Verify `/staticfiles/` exists after deployment

### Audio upload fails
- Verify `SUPABASE_SERVICE_KEY` is set
- Check `audio-files` bucket exists in Supabase
- Verify CORS headers allow Vercel frontend

### Migrations fail
- Check `render.yaml` → `buildCommand` includes `python manage.py migrate`
- Verify `DATABASE_URL` points to writable PostgreSQL
- Check migrations are committed to git

## 📋 Post-Deployment Checklist

- [ ] Build succeeded (check Render logs)
- [ ] No database errors in logs
- [ ] Health check endpoint returns 200
- [ ] Frontend (Vercel) can reach `/api/` endpoints
- [ ] CORS headers allow frontend origin
- [ ] Audio uploads successfully to bucket
- [ ] Transcriptions process correctly
- [ ] JWT tokens validate properly

## 🔗 Important Links

- **Render Dashboard:** https://dashboard.render.com
- **Supabase Dashboard:** https://app.supabase.com
- **Frontend URL:** https://front-decifrae.vercel.app
- **API Base URL:** https://api-decifrae.onrender.com/api/

## ⚠️ Security Notes

- Never commit `.env` to git (use `.env.example` template)
- Rotate `SECRET_KEY` before production
- Use Supabase service key only on backend (never expose)
- HTTPS enforced in production (`SECURE_SSL_REDIRECT=True`)
- HSTS enabled (strict transport security)

---

**Status:** ✅ **READY FOR DEPLOYMENT**

All code changes merged, tests passing, configuration complete.
