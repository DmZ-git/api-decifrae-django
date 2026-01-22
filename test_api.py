#!/usr/bin/env python
"""
Script para testar a API localmente
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.core.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from api.models import AudioFile, ProcessingJob
from api.utils import chord_classifier

def test_chord_classifier():
    """Testa o classificador de acordes"""
    print("\n" + "="*60)
    print("TESTE 1: Classificador de Acordes")
    print("="*60)
    
    # Criar um arquivo de áudio de teste
    import tempfile
    import numpy as np
    import librosa
    
    try:
        # Gerar áudio de teste (seno simples)
        sr = 11025
        duration = 5  # 5 segundos
        freq = 440  # A4
        
        t = np.linspace(0, duration, int(sr * duration))
        y = np.sin(2 * np.pi * freq * t).astype(np.float32)
        
        # Salvar em arquivo temporário
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            import soundfile as sf
            sf.write(tmp.name, y, sr)
            tmp_path = tmp.name
        
        print(f"✅ Arquivo de teste criado: {tmp_path}")
        
        # Testar processamento com beat tracking
        print("\n🔍 Testando beat tracking...")
        result_beat = chord_classifier.processar_audio(tmp_path, metodo='beat')
        print(f"✅ Beat tracking resultado: {result_beat.get('sucesso')}")
        if result_beat.get('sucesso'):
            print(f"   - Acordes detectados: {result_beat.get('quantidade_acordes')}")
            print(f"   - Duração: {result_beat.get('duracao_total')}s")
            print(f"   - Tempo de processamento: {result_beat.get('tempo_processamento_ms')}ms")
        else:
            print(f"   ❌ Erro: {result_beat.get('erro')}")
        
        # Testar processamento com onset detection
        print("\n🔍 Testando onset detection...")
        result_onset = chord_classifier.processar_audio(tmp_path, metodo='onset')
        print(f"✅ Onset detection resultado: {result_onset.get('sucesso')}")
        if result_onset.get('sucesso'):
            print(f"   - Acordes detectados: {result_onset.get('quantidade_acordes')}")
        else:
            print(f"   ❌ Erro: {result_onset.get('erro')}")
        
        # Limpar
        os.unlink(tmp_path)
        print("\n✅ TESTE 1 CONCLUÍDO COM SUCESSO")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_models():
    """Testa os models do Django"""
    print("\n" + "="*60)
    print("TESTE 2: Models Django")
    print("="*60)
    
    try:
        # Contar audiofiles existentes
        audio_count = AudioFile.objects.count()
        print(f"✅ AudioFile objects: {audio_count}")
        
        # Listar os primeiros
        if audio_count > 0:
            audio_files = AudioFile.objects.all()[:3]
            for af in audio_files:
                print(f"   - {af.id}: {af.title} ({af.file_size} bytes)")
        
        print("✅ TESTE 2 CONCLUÍDO COM SUCESSO")
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*60)
    print("TESTES DA API DECIFRAE")
    print("="*60)
    
    test1 = test_models()
    test2 = test_chord_classifier()
    
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)
    print(f"Models Django: {'✅ PASSOU' if test1 else '❌ FALHOU'}")
    print(f"Classificador: {'✅ PASSOU' if test2 else '❌ FALHOU'}")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
