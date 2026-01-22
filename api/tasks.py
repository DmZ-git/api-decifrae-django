"""
Tasks assíncronas para processamento de áudio
"""
import logging
import os
import tempfile
import gc
from celery import shared_task
import requests

from api.utils import chord_classifier
from api.models import AudioFile, Transcription, ProcessingJob

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # Retry após 1 minuto
    soft_time_limit=300,  # 5 minutos soft limit
    time_limit=360,  # 6 minutos hard limit
    acks_late=True,  # Confirma apenas após completar
    reject_on_worker_lost=True,  # Rejeita se worker morrer
)
def processar_audio_async(self, audio_file_id: int, file_url: str):
    """
    Task assíncrona para processar áudio.
    Executa em background sem bloquear requisição HTTP.
    """
    job = None
    tmp_path = None
    
    try:
        # Pega o AudioFile e ProcessingJob
        audio_file = AudioFile.objects.get(id=audio_file_id)
        
        # Atualiza status
        job = ProcessingJob.objects.get(audio_file=audio_file, status='processing')
        job.progress = 30
        job.save()
        
        logger.info(f"Iniciando processamento de áudio {audio_file_id}")
        
        # Baixa arquivo com timeout e controle de memória
        try:
            logger.info(f"Baixando áudio: {file_url}")
            response = requests.get(file_url, timeout=60, stream=True)
            response.raise_for_status()
            
            # Verifica tamanho antes de baixar
            content_length = response.headers.get('content-length')
            if content_length and int(content_length) > 50 * 1024 * 1024:  # 50MB
                raise ValueError("Arquivo muito grande (>50MB)")
            
            # Salva em arquivo temporário com streaming (não carrega tudo na memória)
            suffix = os.path.splitext(file_url)[1] or '.mp3'
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                # Download em chunks menores (4KB ao invés de 8KB)
                # e com limite de tamanho total
                total_downloaded = 0
                max_size = 50 * 1024 * 1024  # 50MB
                
                for chunk in response.iter_content(chunk_size=4096):
                    if chunk:
                        total_downloaded += len(chunk)
                        if total_downloaded > max_size:
                            raise ValueError("Arquivo excedeu limite durante download")
                        tmp.write(chunk)
                        tmp.flush()  # Force flush para liberar buffer
                tmp_path = tmp.name
            
            job.progress = 50
            job.save()
            
            # Força liberação de memória após download
            import gc
            gc.collect()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao baixar arquivo: {e}")
            raise self.retry(exc=e)
        
        # Processa áudio
        logger.info(f"Processando áudio do arquivo: {tmp_path}")
        # Usa beat tracking por padrão (mais rápido e estável)
        result = chord_classifier.detectar_acordes(tmp_path)
        
        if not result.get('sucesso', False):
            error_msg = result.get('erro', 'Erro desconhecido')
            logger.error(f"Erro ao processar áudio: {error_msg}")
            job.status = 'failed'
            job.progress = 100
            job.error_message = error_msg
            job.save()
            return {'success': False, 'error': error_msg}
        
        job.progress = 75
        job.save()
        
        # Prepara dados para salvar
        chords_data = [{
            'acorde': a.get('acorde'),
            'tempo_inicio': a.get('tempo_inicio'),
            'duracao': a.get('duracao'),
            'confianca': a.get('confianca'),
        } for a in result.get('acordes', [])]
        
        metadata = {
            'duracao_total': result.get('duracao_total'),
            'taxa_amostragem': result.get('taxa_amostragem'),
            'total_acordes': result.get('quantidade_acordes'),
        }
        
        # Cria Transcription
        transcription = Transcription.objects.create(
        audio_file=audio_file,
        user=audio_file.user,
        title=f"{audio_file.title} - Cifra",
        chords=result["timestamps"],
        confidence=0.85,
        )
        
        # Atualiza job
        job.status = 'completed'
        job.progress = 100
        job.result = {
            "chords": result["chords"],
            "total": len(result["timestamps"]),
        }
        job.save()
        
        # Atualiza AudioFile
        audio_file.status = 'completed'
        audio_file.save()
        
        # Libera memória após processamento
        import gc
        gc.collect()
        
        logger.info(f"Processamento concluído para áudio {audio_file_id}")
        
        return {
            'success': True,
            'transcription_id': transcription.id,
            'total_acordes': len(chords_data),
            'metadata': metadata,
        }
        
    except self.MaxRetriesExceededError:
        logger.error(f"Máximo de tentativas excedidas para áudio {audio_file_id}")
        if job:
            job.status = 'failed'
            job.progress = 100
            job.error_message = 'Máximo de tentativas excedidas'
            job.save()
        return {'success': False, 'error': 'Máximo de tentativas excedidas'}
        
    except Exception as e:
        logger.exception(f"Erro ao processar áudio {audio_file_id}: {e}")
        if job:
            job.status = 'failed'
            job.progress = 100
            job.error_message = str(e)
            job.save()
        
        # Retry com backoff exponencial
        raise self.retry(exc=e)
        
    finally:
        # Limpa arquivo temporário
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
                logger.info(f"Arquivo temporário removido: {tmp_path}")
            except Exception as e:
                logger.warning(f"Erro ao remover arquivo temporário: {e}")
