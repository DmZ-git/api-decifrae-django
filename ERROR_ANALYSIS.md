# DECIFRAE API - Análise de Erro 400 e HTTP/2

## 🔴 Problemas Identificados

### 1. **Erro 400 Bad Request ao acessar `/audio/:1`**
   - **Causa**: Falta de implementação customizada do método `retrieve()` na classe `AudioFileViewSet`
   - **Detalhe**: O DRF tenta serializar toda a resposta, mas há incompatibilidades com os headers

### 2. **Erro HTTP/2 Protocol Error**
   - **Causa**: Headers malformados na resposta de streaming de arquivo
   - **Detalhe**: Response não tinha configurações adequadas para streaming de arquivos grandes

### 3. **Problema na geração de cifras do MP3**
   - **Causa**: Arquivo de áudio não era retornado corretamente para processamento
   - **Detalhe**: A chain de processamento não conseguia acessar a URL do Supabase

---

## ✅ Soluções Implementadas

### 1. **Adicionado método customizado `retrieve()` em `AudioFileViewSet`**
   
```python
def retrieve(self, request, *args, **kwargs):
    """
    Retrieve audio file metadata OU stream do arquivo.
    
    Query parameters:
    - download=true: Stream do arquivo de áudio
    - download=false ou omitido: JSON metadata
    """
```

**Features**:
- ✅ Retorna JSON metadata por padrão
- ✅ Suporta streaming de arquivo com `?download=true`
- ✅ Headers corretos para audio MIME type
- ✅ Tratamento de timeouts e erros
- ✅ Logging de erros para debug

### 2. **Headers HTTP Corretos para Streaming**
```python
streaming_response['Content-Type'] = 'audio/mpeg'
streaming_response['Accept-Ranges'] = 'bytes'
streaming_response['Cache-Control'] = 'public, max-age=3600'
streaming_response['Content-Disposition'] = 'inline; filename="..."'
```

### 3. **Configurações no `settings.py`**
- `DATA_UPLOAD_MAX_MEMORY_SIZE = 52MB`
- `FILE_UPLOAD_MAX_MEMORY_SIZE = 52MB`
- `SECURE_PROXY_SSL_HEADER` para reverse proxies (Render)

### 4. **Imports Adicionados**
```python
from django.http import FileResponse, StreamingHttpResponse
import requests
import logging
```

---

## 🔧 Como Usar

### Para obter metadados do arquivo (JSON):
```bash
GET /api/audio/1/
Authorization: Bearer <SUPABASE_JWT_TOKEN>

# Retorna JSON:
{
    "id": 1,
    "title": "My Song",
    "file_url": "https://...",
    "format": "mp3",
    "status": "completed",
    ...
}
```

### Para fazer download/stream do arquivo:
```bash
GET /api/audio/1/?download=true
Authorization: Bearer <SUPABASE_JWT_TOKEN>

# Retorna arquivo MP3 com headers corretos
```

---

## 🚀 Próximos Passos para Processamento de Áudio

Para que o processamento de cifras funcione:

1. **Certifique-se que a URL do Supabase é pública**:
   - Verifique em Supabase Storage > Policies
   - A URL deve ser acessível sem autenticação

2. **Use a URL do arquivo para processar**:
```python
# Em tasks.py ou services/audio_processing_client.py:
audio_url = audio_file.file_url  # URL pública do Supabase
# Passar para serviço de detecção de acordes
```

3. **Validação de URL**:
```python
def process_audio(file_url):
    # Verificar se URL é válida e acessível
    response = requests.head(file_url, timeout=5)
    if response.status_code != 200:
        raise ValueError(f"Arquivo inacessível: {response.status_code}")
```

---

## 📋 Checklist de Validação

- [x] Método `retrieve()` customizado implementado
- [x] Headers HTTP corretos para streaming
- [x] Tratamento de timeouts e erros
- [x] Logging adicionado
- [x] Configurações de tamanho de arquivo
- [x] Suporte para query parameter `download`
- [ ] Testar com arquivo MP3 real
- [ ] Validar processamento de cifras após obtenção do arquivo
- [ ] Testar em produção (Render.com)

---

## 🐛 Se ainda houver erros:

1. **Cheque logs do servidor**:
```bash
# Em Render.com
tail -f ~/.render/logs/app.log
```

2. **Teste a URL do arquivo**:
```bash
curl -I "https://...supabase.co/storage/v1/object/public/audio-files/..."
```

3. **Verifique authentication**:
```bash
# Valide seu token Supabase
curl -H "Authorization: Bearer YOUR_TOKEN" https://api-decifrae.onrender.com/api/audio/1/
```

---

## 📝 Modificações Realizadas

**Arquivos alterados**:
1. `api/views.py` - Adicionado método `retrieve()` e imports
2. `api/core/settings.py` - Adicionadas configurações de streaming e logging

**Sem quebra de compatibilidade**: Todas as mudanças são retrocompatíveis ✅
