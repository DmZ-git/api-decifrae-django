"""
Script de teste para validar todos os endpoints do backend Django.
Usa requests para fazer chamadas HTTP e verifica se os endpoints existem.
"""

import requests
import sys
from datetime import datetime

# Configuração
BACKEND_URL = "https://api-decifrae.onrender.com"  # Mudar para local se necessário
# BACKEND_URL = "http://127.0.0.1:8000"  # Para testar localmente

def test_endpoint(method, path, expected_status_codes=[200, 201, 400, 401, 403], description=""):
    """Testa um endpoint e verifica se retorna status válido (não 404)"""
    url = f"{BACKEND_URL}{path}"
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, timeout=10)
        elif method == "OPTIONS":
            response = requests.options(url, timeout=10)
        else:
            print(f"❌ Método {method} não implementado no teste")
            return False
        
        status = response.status_code
        
        if status == 404:
            print(f"❌ {method} {path} - 404 NOT FOUND - {description}")
            return False
        elif status in expected_status_codes:
            print(f"✅ {method} {path} - {status} - {description}")
            return True
        else:
            print(f"⚠️  {method} {path} - {status} (esperado: {expected_status_codes}) - {description}")
            return True  # Endpoint existe, mas retornou status inesperado
    
    except requests.exceptions.ConnectionError:
        print(f"🔌 {method} {path} - CONNECTION ERROR - Backend offline ou URL incorreta")
        return False
    except requests.exceptions.Timeout:
        print(f"⏱️  {method} {path} - TIMEOUT - Backend demorou muito para responder")
        return False
    except Exception as e:
        print(f"❌ {method} {path} - ERRO: {e}")
        return False

def main():
    print("=" * 70)
    print("🧪 TESTE DE ENDPOINTS - BACKEND DJANGO")
    print(f"Backend: {BACKEND_URL}")
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 70)
    print()
    
    tests = []
    
    # Root API
    print("📍 ROOT ENDPOINTS")
    tests.append(test_endpoint("GET", "/api/", [200, 301], "API Root"))
    tests.append(test_endpoint("GET", "/admin/", [200, 301, 302], "Django Admin"))
    print()
    
    # Audio endpoints
    print("📍 AUDIO ENDPOINTS")
    tests.append(test_endpoint("GET", "/api/audio/", [200, 401, 403], "Listar áudios"))
    tests.append(test_endpoint("POST", "/api/audio/", [400, 401, 403], "Criar áudio (sem arquivo)"))
    tests.append(test_endpoint("GET", "/api/audio/123/", [404, 401, 403], "Detalhe áudio (ID fictício)"))
    tests.append(test_endpoint("POST", "/api/audio/123/process/", [404, 401, 403, 400], "Processar áudio (CRÍTICO!)"))
    print()
    
    # Transcription endpoints
    print("📍 TRANSCRIPTION ENDPOINTS")
    tests.append(test_endpoint("GET", "/api/transcriptions/", [200, 401, 403], "Listar transcrições"))
    tests.append(test_endpoint("POST", "/api/transcriptions/", [400, 401, 403], "Criar transcrição"))
    tests.append(test_endpoint("GET", "/api/transcriptions/123/", [404, 401, 403], "Detalhe transcrição"))
    print()
    
    # Job endpoints
    print("📍 JOB ENDPOINTS")
    tests.append(test_endpoint("GET", "/api/jobs/", [200, 401, 403], "Listar jobs"))
    tests.append(test_endpoint("GET", "/api/jobs/123/", [404, 401, 403], "Detalhe job"))
    tests.append(test_endpoint("GET", "/api/jobs/123/status/", [404, 401, 403], "Status job"))
    print()
    
    # Playlist endpoints
    print("📍 PLAYLIST ENDPOINTS")
    tests.append(test_endpoint("GET", "/api/playlists/", [200, 401, 403], "Listar playlists"))
    tests.append(test_endpoint("POST", "/api/playlists/", [400, 401, 403], "Criar playlist"))
    tests.append(test_endpoint("GET", "/api/playlists/123/", [404, 401, 403], "Detalhe playlist"))
    tests.append(test_endpoint("POST", "/api/playlists/123/add_transcription/", [404, 400, 401, 403], "Adicionar à playlist"))
    tests.append(test_endpoint("POST", "/api/playlists/123/remove_transcription/", [404, 400, 401, 403], "Remover da playlist"))
    print()
    
    # CORS test
    print("📍 CORS TEST")
    tests.append(test_endpoint("OPTIONS", "/api/audio/", [200, 204], "CORS preflight"))
    print()
    
    # Resultado final
    print("=" * 70)
    passed = sum(tests)
    total = len(tests)
    percentage = (passed / total * 100) if total > 0 else 0
    
    print(f"RESULTADO: {passed}/{total} testes passaram ({percentage:.1f}%)")
    
    if passed == total:
        print("✅ Todos os endpoints estão funcionando!")
        sys.exit(0)
    elif passed == 0:
        print("❌ Nenhum endpoint funciona. Backend pode estar offline.")
        sys.exit(1)
    else:
        print("⚠️  Alguns endpoints estão com problemas.")
        sys.exit(1)

if __name__ == "__main__":
    main()
