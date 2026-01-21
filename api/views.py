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
        Processa o áudio imediatamente usando o classificador central de acordes.
        Baixa do Supabase via service key e faz processamento síncrono.
        
        POST /api/audio/{id}/process/
        """
        audio_file = self.get_object()
        
        job = ProcessingJob.objects.create(
            audio_file=audio_file,
            job_type='chord_detection',
            status='processing',
            progress=10,
            parameters={'file_url': audio_file.file_url}
        )
        
        tmp_path = None
        try:
            job.progress = 20
            job.save()
            
            # Tenta baixar via Supabase service key primeiro (mais seguro)
            try:
                logger.info(f"Tentando download via Supabase service key: {audio_file.file_url}")
                file_bytes = supabase_client.download_audio_by_url(audio_file.file_url)
                
                suffix = os.path.splitext(audio_file.file_url)[1] or '.mp3'
                with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                    tmp.write(file_bytes)
                    tmp_path = tmp.name
                
                job.progress = 40
                job.save()
                
                processing_result = AudioProcessingService.processar_audio(tmp_path)
                
            except Exception as supabase_err:
                logger.warning(f"Download via Supabase falhou, usando fallback HTTP: {supabase_err}")
                job.progress = 30
                job.save()
                processing_result = AudioProcessingService.processar_audio_url(audio_file.file_url)
            
            if not processing_result.get('success'):
                job.status = 'failed'
                job.progress = 100
                job.error_message = processing_result.get('error', 'Erro ao processar áudio')
                job.save()
                
                return Response(
                    {'error': job.error_message},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            job.progress = 70
            job.save()
            
            chords_data = processing_result.get('chords', [])
            metadata = processing_result.get('metadata', {})
            
            transcription = Transcription.objects.create(
                audio_file=audio_file,
                user=audio_file.user if audio_file.user else request.user if request.user.is_authenticated else None,
                title=f"{audio_file.title} - Cifra",
                chords=chords_data,
                confidence=0.85,
                key=None,
                bpm=None,
                tempo_map=None,
                lyrics=None,
                artist=None,
                notes=None,
            )
            
            job.status = 'completed'
            job.progress = 100
            job.result = {
                'transcription_id': transcription.id,
                'total_acordes': len(chords_data),
                'metadata': metadata,
            }
            job.save()
            
            audio_file.status = 'completed'
            audio_file.save()
            
            return Response({
                'success': True,
                'message': 'Processamento concluído',
                'job_id': job.id,
                'transcription_id': transcription.id,
                'total_acordes': len(chords_data),
                'metadata': metadata,
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Erro ao processar áudio {audio_file.id}: {e}")
            job.status = 'failed'
            job.progress = 100
            job.error_message = f"Erro: {str(e)}"
            job.save()
            
            return Response(
                {'error': job.error_message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)


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
