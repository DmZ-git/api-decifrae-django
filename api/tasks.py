"""
Tasks assíncronas do Celery para processamento de áudio
"""
from celery import shared_task
from .models import ProcessingJob, Transcription
from .services.audio_processing_client import AudioProcessingService
import logging
import tempfile
import os
import requests

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def processar_audio_task(self, job_id):
    """
    Task para processar áudio e detectar acordes
    
    Args:
        job_id: ID do ProcessingJob
    """
    try:
        job = ProcessingJob.objects.get(id=job_id)
        
        # Atualiza status para processando
        job.status = 'processing'
        job.progress = 10
        job.save()
        
        logger.info(f"[Task] Iniciando processamento do job {job_id}")
        logger.info(f"[Task] Arquivo: {job.audio_file.file_url}")
        
        # Baixa o arquivo de áudio
        job.progress = 20
        job.save()
        
        response = requests.get(job.audio_file.file_url, timeout=60)
        response.raise_for_status()
        
        # Salva em arquivo temporário
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name
        
        logger.info(f"[Task] Arquivo baixado para: {tmp_path}")
        
        # Processa o áudio
        job.progress = 30
        job.save()
        
        result = AudioProcessingService.processar_audio(tmp_path)
        
        # Limpa arquivo temporário
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        
        if not result['success']:
            job.status = 'failed'
            job.error_message = result.get('error', 'Erro desconhecido')
            job.save()
            logger.error(f"[Task] Erro no processamento: {job.error_message}")
            return
        
        job.progress = 80
        job.save()
        
        # Cria a transcrição com os acordes detectados
        chords_data = result.get('chords', [])
        metadata = result.get('metadata', {})
        
        # Extrai informações dos acordes
        acordes_str = ' -> '.join([c['acorde'] for c in chords_data])
        
        transcription = Transcription.objects.create(
            audio_file=job.audio_file,
            user=job.audio_file.user,
            title=f"{job.audio_file.title} - Cifra",
            chords=chords_data,
            confidence=0.85,  # Confiança média (pode ser calculada)
            key=None,  # Será preenchido manualmente ou com análise extra
            bpm=None   # Será preenchido manualmente ou com análise extra
        )
        
        job.progress = 90
        job.result = {
            'transcription_id': transcription.id,
            'total_acordes': len(chords_data),
            'acordes': acordes_str,
            'metadata': metadata
        }
        job.save()
        
        logger.info(f"[Task] Transcrição criada: {transcription.id}")
        
        # Marca como completo
        job.status = 'completed'
        job.progress = 100
        job.save()
        
        logger.info(f"[Task] Job {job_id} completado com sucesso")
        
    except ProcessingJob.DoesNotExist:
        logger.error(f"[Task] Job {job_id} não encontrado")
    except Exception as e:
        logger.error(f"[Task] Erro no processamento: {str(e)}")
        try:
            job = ProcessingJob.objects.get(id=job_id)
            job.status = 'failed'
            job.error_message = f"Erro: {str(e)}"
            job.save()
        except:
            pass


@shared_task
def cleanup_old_jobs():
    """
    Task para limpar jobs antigos (mantém últimos 100)
    Pode ser agendada com Celery Beat
    """
    from django.utils import timezone
    from datetime import timedelta
    
    # Mantém apenas jobs dos últimos 30 dias
    cutoff_date = timezone.now() - timedelta(days=30)
    old_jobs = ProcessingJob.objects.filter(created_at__lt=cutoff_date)
    deleted_count = old_jobs.delete()[0]
    
    logger.info(f"Limpeza: {deleted_count} jobs antigos deletados")
