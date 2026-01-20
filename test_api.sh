#!/bin/bash
# Script para testar os endpoints da API DECIFRAE

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configurações
BASE_URL="https://api-decifrae.onrender.com/api"
# BASE_URL="http://localhost:8000/api"  # Para desenvolvimento local

# Você deve obter este token de autenticação do Supabase
BEARER_TOKEN="${1:-}"

if [ -z "$BEARER_TOKEN" ]; then
    echo -e "${RED}❌ Erro: Token JWT do Supabase não fornecido${NC}"
    echo ""
    echo "Uso: $0 <seu_token_jwt>"
    echo ""
    echo "Como obter o token:"
    echo "1. Faça login em seu frontend (Supabse)"
    echo "2. Abra o DevTools (F12)"
    echo "3. No Console, execute: console.log(localStorage.getItem('sb-access-token'))"
    echo "4. Copie o token e passe como argumento"
    exit 1
fi

echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
echo "TESTES DA API DECIFRAE"
echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
echo ""

# Test 1: Verificar autenticação
echo -e "${YELLOW}[TEST 1]${NC} Verificando autenticação..."
AUTH_RESPONSE=$(curl -s -X GET "${BASE_URL}/auth/me/" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" \
  -H "Content-Type: application/json")

if echo "$AUTH_RESPONSE" | grep -q '"success": true'; then
    echo -e "${GREEN}✅ Autenticação OK${NC}"
    echo "Usuário: $(echo $AUTH_RESPONSE | grep -o '"first_name":"[^"]*' | cut -d'"' -f4)"
else
    echo -e "${RED}❌ Falha na autenticação${NC}"
    echo "Response: $AUTH_RESPONSE"
    exit 1
fi
echo ""

# Test 2: Listar áudios
echo -e "${YELLOW}[TEST 2]${NC} Listando arquivos de áudio..."
AUDIO_LIST=$(curl -s -X GET "${BASE_URL}/audio/" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" \
  -H "Content-Type: application/json")

AUDIO_COUNT=$(echo "$AUDIO_LIST" | grep -o '"id":' | wc -l)
echo -e "${GREEN}✅ ${AUDIO_COUNT} arquivo(s) encontrado(s)${NC}"
echo "Response (primeiros 200 chars): ${AUDIO_LIST:0:200}..."
echo ""

# Test 3: Testar acesso a arquivo específico (metadata)
if [ "$AUDIO_COUNT" -gt 0 ]; then
    echo -e "${YELLOW}[TEST 3]${NC} Obtendo metadata do primeiro arquivo..."
    FIRST_AUDIO_ID=$(echo "$AUDIO_LIST" | grep -o '"id":[0-9]*' | head -1 | grep -o '[0-9]*')
    
    METADATA=$(curl -s -X GET "${BASE_URL}/audio/${FIRST_AUDIO_ID}/" \
      -H "Authorization: Bearer ${BEARER_TOKEN}" \
      -H "Content-Type: application/json")
    
    if echo "$METADATA" | grep -q '"title"'; then
        echo -e "${GREEN}✅ Metadata obtida com sucesso${NC}"
        echo "ID: $FIRST_AUDIO_ID"
        echo "Title: $(echo $METADATA | grep -o '"title":"[^"]*' | cut -d'"' -f4)"
        echo ""
        
        # Test 4: Testar streaming do arquivo
        echo -e "${YELLOW}[TEST 4]${NC} Testando download/streaming do arquivo..."
        echo "URL: ${BASE_URL}/audio/${FIRST_AUDIO_ID}/?download=true"
        
        STREAM_TEST=$(curl -s -I -X GET "${BASE_URL}/audio/${FIRST_AUDIO_ID}/?download=true" \
          -H "Authorization: Bearer ${BEARER_TOKEN}")
        
        if echo "$STREAM_TEST" | grep -q "200 OK\|200 "; then
            echo -e "${GREEN}✅ Arquivo acessível para download/streaming${NC}"
            echo "Content-Type: $(echo "$STREAM_TEST" | grep -i 'Content-Type' | head -1)"
            echo "Accept-Ranges: $(echo "$STREAM_TEST" | grep -i 'Accept-Ranges' | head -1)"
        else
            echo -e "${RED}❌ Erro ao acessar arquivo para download${NC}"
            echo "Response headers:"
            echo "$STREAM_TEST" | head -10
        fi
    else
        echo -e "${RED}❌ Falha ao obter metadata${NC}"
        echo "Response: $METADATA"
    fi
else
    echo -e "${YELLOW}⚠️  Nenhum arquivo encontrado - pulando testes de arquivo${NC}"
fi
echo ""

# Test 5: Listar transcrições/cifras
echo -e "${YELLOW}[TEST 5]${NC} Listando transcrições/cifras..."
TRANS_LIST=$(curl -s -X GET "${BASE_URL}/transcriptions/" \
  -H "Authorization: Bearer ${BEARER_TOKEN}" \
  -H "Content-Type: application/json")

TRANS_COUNT=$(echo "$TRANS_LIST" | grep -o '"id":' | wc -l)
echo -e "${GREEN}✅ ${TRANS_COUNT} transcrição(ões) encontrada(s)${NC}"
echo ""

echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ TESTES CONCLUÍDOS COM SUCESSO${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════${NC}"
echo ""
echo "Dicas:"
echo "  • Se receber erro 400 em /audio/:id/, verifique o UUID do arquivo"
echo "  • Se streaming retornar erro, valide que URL do Supabase é pública"
echo "  • Para processamento de cifras, use: POST /api/jobs/process_audio/"
