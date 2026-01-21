# ✅ CHECKLIST DE DEPLOYMENT - Otimizações de Memória

## 📋 Resumo Executivo

Implementei **processamento assíncrono com Celery + Redis** + **otimizações de memória no librosa** para resolver o problema de OOM no Render.

**Resultado esperado**: 
- ❌ ANTES: Worker timeout + SIGKILL por OOM
- ✅ DEPOIS: Requisições retornam em <100ms, processamento em background

---

## 🚀 Passo a Passo para Deploy

### FASE 1: Adicionar Redis no Render (5 min)

```
1. Login no Render Dashboard
2. Novo → Database → Redis (Free plan)
3. Nome: redis-cache
4. Copiar Connection String
5. Salvar em algum lugar seguro
```

### FASE 2: Atualizar Environment Variables (10 min)

No Render Dashboard → API Service → Environment:

```bash
# Copie essas linhas e SUBSTITUA os values:

CELERY_BROKER_URL=redis://:PASSWORD@HOST:PORT/0
CELERY_RESULT_BACKEND=redis://:PASSWORD@HOST:PORT/0

ENVIRONMENT=production

# Exemplo real (alterar values):
CELERY_BROKER_URL=redis://:abc123xyz@red-abc123def456.onrender.com:6379/0
CELERY_RESULT_BACKEND=redis://:abc123xyz@red-abc123def456.onrender.com:6379/0
```

### FASE 3: Deploy de Código (5 min)

```bash
cd api-decifrae

# Commit das mudanças
git add -A
git commit -m "feat: Processamento assíncrono com Celery + Otimização de memória"
git push

# Render detecta automaticamente e faz deploy
```

### FASE 4: Adicionar Background Worker no Render (10 min)

Na pasta raiz, arquivo `render.yaml` já foi atualizado com:

```yaml
- type: background_worker
  name: celery-worker-audio
  ...
```

Render detecta `render.yaml` automaticamente.

### FASE 5: Testar (5 min)

```bash
# 1. Upload um arquivo MP3
curl -X POST https://api-decifrae.onrender.com/api/audio/ \
  -F "file=@song.mp3" \
  -F "title=Minha Música"

# Response: 201 Created
# {
#   "id": 1,
#   "file_url": "https://...",
#   "status": "uploaded"
# }

# 2. Iniciar processamento (NOVO - assíncrono)
curl -X POST https://api-decifrae.onrender.com/api/audio/1/process/

# Response: 202 Accepted (NÃO ESPERA PROCESSAR!)
# {
#   "job_id": 123,
#   "task_id": "abc123xyz",
#   "message": "Processamento iniciado"
# }

# 3. Consultar status
curl https://api-decifrae.onrender.com/api/processing-jobs/123/status/

# Response: 200 OK
# {
#   "status": "processing",  # ou "completed"
#   "progress": 65,
#   "result": {
#     "transcription_id": 5,
#     "total_acordes": 32,
#     ...
#   }
# }
```

---

## 📁 Arquivos Criados/Modificados

### ✅ CRIADOS (Novos)

| Arquivo | Função |
|---------|--------|
| `api/celery_config.py` | Configuração Celery |
| `api/tasks.py` | Task assíncrona de processamento |
| `OPTIMIZATION_GUIDE.md` | Guia técnico completo |
| `.env.example` | Variáveis de ambiente (atualizado) |

### ✏️ MODIFICADOS

| Arquivo | Mudança |
|---------|---------|
| `requirements.txt` | +celery, +redis |
| `api/core/settings.py` | +Configurações Celery |
| `api/views.py` | Endpoint `/process/` agora é assíncrono |
| `api/utils/chord_classifier.py` | Otimizações de memória |
| `api/__init__.py` | Import Celery app |
| `render.yaml` | +background_worker, +redis |

---

## 🧪 Teste Local Antes de Deploy

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Django
python manage.py runserver

# Terminal 3: Celery Worker
celery -A api worker -l info

# Terminal 4: Testar (noutra janela)
python manage.py shell
>>> from api.tasks import processar_audio_async
>>> task = processar_audio_async.delay(1, "https://exemplo.com/audio.mp3")
>>> task.status
'PENDING'  # Depois de alguns segundos
>>> task.status
'SUCCESS'  # ou 'FAILURE'
```

---

## ⚠️ Possíveis Problemas & Soluções

### ❌ Problema: "Redis connection refused"

```
Causa: CELERY_BROKER_URL incorreta ou vazia
Solução:
1. Copiar Connection String do Redis no Render
2. Colar em CELERY_BROKER_URL (sem mudar)
3. Fazer redeploy: git push
```

### ❌ Problema: "Worker not found" ou tasks na fila

```
Causa: Background worker não iniciado
Solução:
1. Ir ao Render Dashboard
2. Services → celery-worker-audio
3. Verificar Status (deve ser "Live")
4. Se "Build failed", clicar e ver erro no log
```

### ❌ Problema: "Numba LLVM error" ainda aparece

```
Causa: Arquivo > 50MB ou > 300s
Solução: Validações estão no chord_classifier.py
Verificar: Limite é respeitado em upload
```

### ❌ Problema: "Processa tudo, mas não salva resultado"

```
Causa: Database não consegue salvar Transcription
Solução:
1. Verificar migrations: python manage.py migrate
2. Verificar logs do worker: celery -A api worker -l debug
```

---

## 📊 Comparação Performance

### Antes (Bloqueante Síncrono)
```
POST /api/audio/1/process/
├─ Aguarda 10-60 segundos
├─ Worker travado
├─ Se timeout: SIGKILL (Worker down)
└─ Outro cliente: fila de espera
```

**Resultado**: 🔴 ERRO - Worker timeout, OOM

### Depois (Assíncrono Celery)
```
POST /api/audio/1/process/
├─ Retorna 202 em <100ms ✅
├─ Worker liberado ✅
├─ Task enfileirada no Redis ✅
├─ Celery worker processa em background ✅
└─ Cliente faz polling em `/status/` ✅
```

**Resultado**: 🟢 SUCESSO - Sem timeout, sem OOM

---

## 📈 Monitoramento

### Verificar se Celery está rodando

```bash
# No Render, acessar shell do background_worker:
celery -A api inspect active
celery -A api inspect stats

# Ou via logs:
Render Dashboard → celery-worker-audio → Logs
```

### Monitorar uso de memória

```bash
# Render Dashboard → API → Metrics
# Verificar: Memory Usage (deve ficar <200MB agora)
```

---

## 🎉 Sucesso!

Quando tudo estiver funcionando:

✅ Upload de áudio → 201 Created  
✅ POST /process/ → 202 Accepted (em <100ms)  
✅ GET /status/ → mostra progresso  
✅ Nenhum timeout ou OOM  
✅ Múltiplas requisições simultâneas funcionam  

---

## 📞 Suporte

Se algo der errado:

1. **Verificar render.yaml**: Deve ter `type: background_worker`
2. **Verificar env vars**: CELERY_BROKER_URL deve estar preenchida
3. **Verificar logs**: 
   - Render → API service → Logs
   - Render → celery-worker → Logs
4. **Teste local**: Antes de fazer push, testar localmente com Redis

---

## 🔗 Próximas Etapas (Opcional)

- [ ] Adicionar Flower para monitorar Celery (dashboard)
- [ ] Configurar alertas se worker morrer
- [ ] Implementar retry automático com exponential backoff (já feito em tasks.py)
- [ ] Adicionar timeout de arquivo progressivo (se arquivo > 100MB, rejeitar)

