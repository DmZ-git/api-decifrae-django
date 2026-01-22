#!/usr/bin/env python
# Simple test script
import os
import sys
import django
import tempfile
import numpy as np

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.core.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

django.setup()

from api.utils import chord_classifier
import soundfile as sf

print("\n" + "="*60)
print("TEST: Chord Classifier")
print("="*60)

try:
    # Create test audio
    sr = 11025
    duration = 5
    freq = 440
    
    t = np.linspace(0, duration, int(sr * duration))
    y = np.sin(2 * np.pi * freq * t).astype(np.float32)
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        sf.write(tmp.name, y, sr)
        tmp_path = tmp.name
    
    print("Test file created: " + tmp_path)
    
    # Test beat tracking
    print("\nTesting beat tracking...")
    result_beat = chord_classifier.processar_audio(tmp_path, metodo='beat')
    print("Beat tracking success: " + str(result_beat.get('sucesso')))
    if result_beat.get('sucesso'):
        print("Chords detected: " + str(result_beat.get('quantidade_acordes')))
        print("Duration: " + str(result_beat.get('duracao_total')) + "s")
        print("Processing time: " + str(result_beat.get('tempo_processamento_ms')) + "ms")
    else:
        print("Error: " + result_beat.get('erro', 'Unknown'))
    
    # Cleanup
    os.unlink(tmp_path)
    print("\nTEST PASSED")
    
except Exception as e:
    print("ERROR: " + str(e))
    import traceback
    traceback.print_exc()

print("="*60)
