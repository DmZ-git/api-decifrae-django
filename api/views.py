from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import AudioFile, Transcription, ProcessingJob
from .serializers import AudioFileSerializer, TranscriptionSerializer, ProcessingJobSerializer
from .supabase_client import SupabaseClient, supabase_client
from .services.audio_processing_client import AudioProcessingService
from .tasks import processar_audio_async  # Importa task assíncrona
import os
import tempfile
import logging

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class AudioFileViewSet(viewsets.ModelViewSet):
    """ViewSet para operações CRUD de AudioFile"""
    queryset = AudioFile.objects.all()
    serializer_class = AudioFileSerializer
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return AudioFile.objects.filter(user=self.request.user)
        return AudioFile.objects.all()

    def create(self, request, *args, **kwargs):
        """Upload de arquivo de áudio com integração Supabase"""
        file = request.FILES.get('file')
        title = request.data.get('title', 'Sem título')
        
        if not file:
            return Response(
                {'error': 'Nenhum arquivo foi enviado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            import uuid
            file_ext = os.path.splitext(file.name)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = f"{unique_filename}"
            
            supabase_client_inst = SupabaseClient()
            # Garante existência do bucket antes de enviar
            supabase_client_inst.ensure_bucket(os.environ.get('SUPABASE_STORAGE_BUCKET', 'audio-files'))
            file_content = file.read()
            upload_result = supabase_client_inst.upload_audio(
                file_path=file_path,
                file_content=file_content,
                bucket=os.environ.get('SUPABASE_STORAGE_BUCKET', 'audio-files')
            )
            
            if not upload_result.get('success'):
                return Response(
                    {'error': f'Erro ao fazer upload para o Supabase: {upload_result.get("error")}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            user_id = None
            if hasattr(request, 'supabase_user'):
                user_id = request.supabase_user.user.id
            
            audio_file = AudioFile.objects.create(
                user=request.user if request.user.is_authenticated else None,
                title=title,
                file_url=upload_result['public_url'],
                file_name=file.name,
                file_size=file.size,
                format=file_ext.replace('.', ''),
                status='uploaded'
            )
            
            serializer = self.get_serializer(audio_file)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.exception("Erro ao processar upload")
            return Response(
                {'error': f'Erro ao processar upload: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """
        Inicia o processamento de áudio de forma ASSÍNCRONA.
        Retorna imediatamente com job_id para o cliente fazer polling.
        
        POST /api/audio/{id}/process/
        """
        audio_file = self.get_object()
        
        # Validação de tamanho
        max_size_mb = 50
        if audio_file.file_size > max_size_mb * 1024 * 1024:
            return Response(
                {'error': f'Arquivo muito grande. Máximo: {max_size_mb}MB'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cria ProcessingJob
        job = ProcessingJob.objects.create(
            audio_file=audio_file,
            job_type='chord_detection',
            status='queued',
            progress=0,
            parameters={'file_url': audio_file.file_url}
        )
        
        logger.info(f"Job criado: {job.id} para áudio: {audio_file.id}")
        
        # Enfileira task assíncrona
        try:
            task = processar_audio_async.delay(
                audio_file_id=audio_file.id,
                file_url=audio_file.file_url
            )
            job.celery_task_id = task.id
            job.status = 'processing'
            job.progress = 10
            job.save()
            
            logger.info(f"Task Celery enfileirada: {task.id}")
            
            return Response({
                'success': True,
                'message': 'Processamento iniciado',
                'job_id': job.id,
                'task_id': task.id,
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            logger.error(f"Erro ao enfileirar task: {e}", exc_info=True)
            if job:
                job.status = 'failed'
                job.error_message = f'Erro ao iniciar processamento: {str(e)}'
                job.save()
            
            return Response(
                {'error': f'Erro ao iniciar processamento: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TranscriptionViewSet(viewsets.ModelViewSet):
    """ViewSet para operações CRUD de Transcription (Cifras)"""
    queryset = Transcription.objects.all()
    serializer_class = TranscriptionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Transcription.objects.filter(user=self.request.user)
        return Transcription.objects.all()

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()


class ProcessingJobViewSet(viewsets.ModelViewSet):
    """ViewSet para ProcessingJob (rastreamento de processamento)"""
    queryset = ProcessingJob.objects.all()
    serializer_class = ProcessingJobSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return ProcessingJob.objects.filter(audio_file__user=self.request.user)
        return ProcessingJob.objects.all()

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """Retorna o status atual do job"""
        job = self.get_object()
        return Response({
            'status': job.status,
            'progress': job.progress,
            'result': job.result,
            'error_message': job.error_message
        })
