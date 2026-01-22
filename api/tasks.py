"""
Task assíncrona para processamento de áudio e detecção de acordes
"""
import logging
import os
import tempfile
import requests

from celery import shared_task
from django.db import transaction

from api.models import AudioFile, Transcription, ProcessingJob
from api.utils.chord_classifier import detectar_acordes

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=360,
    acks_late=True,
    reject_on_worker_lost=True,
)
def processar_audio_async(self, audio_file_id: int):
    """
    Processa um áudio:
    - baixa do Supabase
    - detecta acordes
    - gera JSON final
    - salva Transcription
    """
    job = None
    tmp_path = None

    try:
        audio_file = AudioFile.objects.get(id=audio_file_id)

        job = ProcessingJob.objects.filter(
            audio_file=audio_file,
            status="processing"
        ).first()

        if not job:
            raise RuntimeError("ProcessingJob não encontrado")

        logger.info(f"Iniciando processamento do áudio {audio_file.id}")
        job.progress = 20
        job.save()

        # ==========================
        # Download do áudio
        # ==========================
        response = requests.get(audio_file.file_url, stream=True, timeout=60)
        response.raise_for_status()

        suffix = os.path.splitext(audio_file.file_url)[1] or ".mp3"

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    tmp.write(chunk)
            tmp_path = tmp.name

        job.progress = 40
        job.save()

        # ==========================
        # Processamento real
        # ==========================
        logger.info(f"Detectando acordes em {tmp_path}")
        result = detectar_acordes(tmp_path)

        if not result:
            raise RuntimeError("Resultado vazio no processamento")

        job.progress = 70
        job.save()

        # ==========================
        # JSON FINAL (PADRÃO)
        # ==========================
        final_json = {
            "chords": result["chords"],
            "content": result["content"],
            "timestamps": result["timestamps"],
        }

        # ==========================
        # Persistência
        # ==========================
        with transaction.atomic():
            transcription = Transcription.objects.create(
                audio_file=audio_file,
                user=audio_file.user,
                title=f"{audio_file.title} - Cifra",
                data=final_json,   # ⬅️ CAMPO JSON
            )

            audio_file.status = "done"
            audio_file.save()

            job.status = "completed"
            job.progress = 100
            job.result = {
                "transcription_id": transcription.id
            }
            job.save()

        logger.info(f"Processamento concluído: áudio {audio_file.id}")

        return {
            "success": True,
            "transcription_id": transcription.id
        }

    except Exception as e:
        logger.exception(f"Erro no processamento do áudio {audio_file_id}")

        if job:
            job.status = "failed"
            job.progress = 100
            job.error_message = str(e)
            job.save()

        raise self.retry(exc=e)

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
