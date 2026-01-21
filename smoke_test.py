#!/usr/bin/env python
"""
Smoke test: upload + process audio via Django views without running server.
Requires Supabase credentials in .env and bucket permissions.
"""
import io
import math
import os
import sys
from pathlib import Path

# Ensure project root in path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Prepare a tiny 0.5s sine wave WAV in memory
import wave
import struct

def generate_wav_bytes(duration_sec=0.5, freq=440.0, framerate=8000, amplitude=0.3):
    nframes = int(duration_sec * framerate)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(framerate)
        for i in range(nframes):
            t = float(i) / framerate
            sample = int(amplitude * 32767.0 * math.sin(2 * math.pi * freq * t))
            wf.writeframes(struct.pack('<h', sample))
    return buf.getvalue()

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.core.settings')
import django
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

def main():
    django.setup()
    client = Client()

    # Generate a small wav file
    audio_bytes = generate_wav_bytes()
    upload_file = SimpleUploadedFile('test.wav', audio_bytes, content_type='audio/wav')

    # Upload
    print('Uploading test audio to /api/audio/...')
    resp = client.post('/api/audio/', data={'title': 'Smoke Test', 'file': upload_file})
    print('Upload status:', resp.status_code)
    try:
        data = resp.json()
    except Exception:
        data = {'raw': resp.content[:200]}
    print('Upload response:', data)
    if resp.status_code != 201 or 'id' not in data:
        print('❌ Upload failed; aborting smoke test')
        return 1

    audio_id = data['id']

    # Process
    print(f'Processing audio id={audio_id} via /api/audio/{audio_id}/process/...')
    resp2 = client.post(f'/api/audio/{audio_id}/process/')
    print('Process status:', resp2.status_code)
    try:
        data2 = resp2.json()
    except Exception:
        data2 = {'raw': resp2.content[:200]}
    print('Process response:', data2)

    ok = resp2.status_code == 200 and data2.get('success')
    print('Result:', '✅ Success' if ok else '❌ Failed')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
