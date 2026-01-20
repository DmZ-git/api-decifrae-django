from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User
from django.http import FileResponse, StreamingHttpResponse, JsonResponse
from django.core.files.storage import default_storage
from .models import AudioFile, Transcription, Playlist, ProcessingJob
from .serializers import (
    AudioFileSerializer, TranscriptionSerializer, PlaylistSerializer, 
    ProcessingJobSerializer, UserSerializer
)
from .supabase_client import SupabaseClient
import uuid
import os
import requests
import logging

logger = logging.getLogger(__name__)


# ==========================================
# Endpoints de Autenticação
# ==========================================

@api_view(['GET'])
def me_view(request):
    """
    Endpoint para obter dados do usuário autenticado
    
    GET /api/auth/me/
    Headers: Authorization: Bearer <SUPABASE_JWT_TOKEN>
    """
    if not request.user.is_authenticated:
        return Response(
            {
                'success': False,
                'error': 'Usuário não autenticado'
            },
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    user_serializer = UserSerializer(request.user)
    return Response(
        {
            'success': True,
            'user': user_serializer.data
        },
        status=status.HTTP_200_OK
    )


@method_decorator(csrf_exempt, name='dispatch')
class AudioFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operações CRUD de AudioFile
    """
    queryset = AudioFile.objects.all()
    serializer_class = AudioFileSerializer
    permission_classes = [IsAuthenticated]  # Apenas usuários autenticados
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        # Retorna apenas os áudios do usuário autenticado
        return AudioFile.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        """
        Upload de arquivo de áudio com integração Supabase
        
        POST /api/audio/
        {
            "file": <arquivo mp3>,
            "title": "Nome da música"
        }
        """
        logger.info(f"Iniciando upload de áudio. Usuário: {request.user}, Autenticado: {request.user.is_authenticated}")
        
        file = request.FILES.get('file')
        title = request.data.get('title', 'Sem título')
        
        if not file:
            logger.warning("Nenhum arquivo enviado na requisição")
            return Response(
                {'error': 'Nenhum arquivo foi enviado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validar autenticação
        if not request.user.is_authenticated:
            logger.warning("Tentativa de upload sem autenticação")
            return Response(
                {'error': 'Autenticação necessária'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            # Gera um nome único para o arquivo
            file_ext = os.path.splitext(file.name)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = f"{unique_filename}"
            
            logger.info(f"Iniciando upload do arquivo: {unique_filename} (original: {file.name}, tamanho: {file.size} bytes)")
            
            # Faz upload para o Supabase Storage
            supabase_client = SupabaseClient()
            file_content = file.read()
            upload_result = supabase_client.upload_audio(
                file_path=file_path,
                file_content=file_content,
                bucket=os.environ.get('SUPABASE_STORAGE_BUCKET', 'audio-files')
            )
            
            if not upload_result.get('success'):
                error_msg = f'Erro ao fazer upload para o Supabase: {upload_result.get("error")}'
                logger.error(error_msg)
                return Response(
                    {'error': error_msg},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            logger.info(f"Upload para Supabase concluído com sucesso. URL: {upload_result['public_url']}")
            
            # Obtém o user_id do Supabase (do token)
            user_id = None
            if hasattr(request, 'supabase_user'):
                user_id = request.supabase_user.user.id
                logger.info(f"Supabase user_id encontrado: {user_id}")
            
            # Salva na tabela audio_files do Supabase
            if user_id:
                audio_data = {
                    'user_id': user_id,
                    'title': title,
                    'file_path': file_path,
                    'storage_url': upload_result['public_url'],
                    'file_size': file.size,
                    'format': file_ext.replace('.', ''),
                    'status': 'completed'
                }
                
                supabase_record = supabase_client.create_audio_file(audio_data)
                
                if supabase_record.get('success'):
                    logger.info(f"Áudio salvo no Supabase: {supabase_record['data']}")
                    # Retorna o registro do Supabase
                    return Response(supabase_record['data'], status=status.HTTP_201_CREATED)
                else:
                    logger.warning(f"Erro ao salvar no Supabase: {supabase_record}")
            
            # Fallback: Cria o registro no banco de dados local
            logger.info(f"Salvando áudio no banco de dados local. Usuário: {request.user}")
            audio_file = AudioFile.objects.create(
                user=request.user,  # Sempre usa o usuário autenticado
                title=title,
                file_url=upload_result['public_url'],
                file_name=file.name,
                file_size=file.size,
                format=file_ext.replace('.', ''),
                status='uploaded'
            )
            
            logger.info(f"Áudio criado com sucesso: ID={audio_file.id}, Title={title}")
            serializer = self.get_serializer(audio_file)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            error_msg = f'Erro ao processar upload: {str(e)}'
            logger.exception(error_msg)  # exception() inclui traceback
            return Response(
                {'error': error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        # Associa o arquivo ao usuário logado se autenticado
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve audio file metadata OR stream the audio file.
        
        Query parameters:
        - download=true: Stream the audio file for download
        - download=false or omitted: Return JSON metadata
        """
        audio_file = self.get_object()
        download = request.query_params.get('download', 'false').lower() == 'true'
        
        if not download:
            # Return metadata as JSON
            serializer = self.get_serializer(audio_file)
            return Response(serializer.data)
        
        # Stream the audio file from Supabase
        try:
            file_url = audio_file.file_url
            
            if not file_url:
                return Response(
                    {'error': 'URL do arquivo não disponível'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Stream the file from Supabase with proper headers
            response = requests.get(file_url, stream=True, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch audio from Supabase: {response.status_code}")
                return Response(
                    {'error': f'Erro ao recuperar arquivo: {response.status_code}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Create streaming response with proper headers for audio
            def generate_chunks():
                try:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            yield chunk
                except Exception as e:
                    logger.error(f"Error streaming audio: {str(e)}")
            
            streaming_response = StreamingHttpResponse(
                generate_chunks(),
                content_type=response.headers.get('Content-Type', 'audio/mpeg')
            )
            
            # Set proper headers for audio streaming
            streaming_response['Content-Length'] = response.headers.get('Content-Length', '')
            streaming_response['Accept-Ranges'] = 'bytes'
            streaming_response['Cache-Control'] = 'public, max-age=3600'
            
            # Set filename for download
            file_name = audio_file.file_name or f"audio{audio_file.format}"
            streaming_response['Content-Disposition'] = f'inline; filename="{file_name}"'
            
            return streaming_response
            
        except requests.Timeout:
            logger.error("Timeout while fetching audio from Supabase")
            return Response(
                {'error': 'Tempo limite excedido ao recuperar arquivo'},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except Exception as e:
            logger.error(f"Error in audio retrieve: {str(e)}")
            return Response(
                {'error': f'Erro ao recuperar arquivo: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TranscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operações CRUD de Transcription (Cifras)
    """
    queryset = Transcription.objects.all()
    serializer_class = TranscriptionSerializer
    permission_classes = [IsAuthenticated]  # Apenas usuários autenticados

    def get_queryset(self):
        # Retorna apenas as transcrições do usuário autenticado
        return Transcription.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PlaylistViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operações CRUD de Playlist
    """
    queryset = Playlist.objects.all()
    serializer_class = PlaylistSerializer
    permission_classes = [IsAuthenticated]  # Apenas usuários autenticados

    def get_queryset(self):
        # Retorna playlists do usuário + públicas de outros
        return Playlist.objects.filter(user=self.request.user) | Playlist.objects.filter(is_public=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def add_transcription(self, request, pk=None):
        """
        Adiciona uma transcrição à playlist
        """
        playlist = self.get_object()
        transcription_id = request.data.get('transcription_id')
        
        try:
            transcription = Transcription.objects.get(id=transcription_id, user=request.user)
            playlist.transcriptions.add(transcription)
            return Response({'status': 'Transcrição adicionada'})
        except Transcription.DoesNotExist:
            return Response({'error': 'Transcrição não encontrada'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def remove_transcription(self, request, pk=None):
        """
        Remove uma transcrição da playlist
        """
        playlist = self.get_object()
        transcription_id = request.data.get('transcription_id')
        
        try:
            transcription = Transcription.objects.get(id=transcription_id)
            playlist.transcriptions.remove(transcription)
            return Response({'status': 'Transcrição removida'})
        except Transcription.DoesNotExist:
            return Response({'error': 'Transcrição não encontrada'}, status=status.HTTP_404_NOT_FOUND)


class ProcessingJobViewSet(viewsets.ModelViewSet):
    """
    ViewSet para ProcessingJob (rastreamento de processamento)
    """
    queryset = ProcessingJob.objects.all()
    serializer_class = ProcessingJobSerializer
    permission_classes = [IsAuthenticated]  # Apenas usuários autenticados

    def get_queryset(self):
        # Retorna jobs dos áudios do usuário autenticado
        return ProcessingJob.objects.filter(audio_file__user=self.request.user)

    @action(detail=True, methods=['get'])
    def status(self, request, pk=None):
        """
        Retorna o status atual do job
        """
        job = self.get_object()
        return Response({
            'status': job.status,
            'progress': job.progress,
            'result': job.result,
            'error_message': job.error_message
        })

    @action(detail=False, methods=['post'])
    def process_audio(self, request):
        """
        Inicia o processamento de áudio para detecção de acordes
        
        POST /api/jobs/process_audio/
        {
            "audio_file_id": 1
        }
        """
        audio_file_id = request.data.get('audio_file_id')
        
        if not audio_file_id:
            return Response(
                {'error': 'audio_file_id é obrigatório'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            audio_file = AudioFile.objects.get(id=audio_file_id, user=request.user)
        except AudioFile.DoesNotExist:
            return Response(
                {'error': 'Arquivo de áudio não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            # Cria um job de processamento
            job = ProcessingJob.objects.create(
                audio_file=audio_file,
                job_type='chord_detection',
                status='pending',
                parameters={'file_url': audio_file.file_url}
            )
            
            # Inicia o processamento assíncrono
            from .tasks import processar_audio_task
            task = processar_audio_task.delay(job.id)
            
            job.celery_task_id = task.id
            job.save()
            
            serializer = ProcessingJobSerializer(job)
            return Response(
                {
                    'success': True,
                    'message': 'Processamento iniciado',
                    'job': serializer.data
                },
                status=status.HTTP_201_CREATED
            )
            
        except Exception as e:
            return Response(
                {'error': f'Erro ao iniciar processamento: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
def home(request):
    """
    Endpoint de boas-vindas da API
    """
    return Response({
        'message': 'Bem-vindo à API DECIFRAE',
        'version': '1.0',
        'endpoints': {
            'audio_files': '/api/audio/',
            'transcriptions': '/api/transcriptions/',
            'playlists': '/api/playlists/',
            'processing_jobs': '/api/jobs/',
            'admin': '/admin/',
        }
    })


@api_view(['GET'])
def help_view(request):
    """
    Endpoint de ajuda
    """
    return Response({
        'message': 'Ajuda da API DECIFRAE',
        'endpoints': {
            'GET /api/': 'Página inicial',
            'GET /api/help/': 'Esta página de ajuda',
            
            'GET /api/audio/': 'Lista todos os áudios do usuário',
            'POST /api/audio/': 'Upload de novo áudio',
            'GET /api/audio/{id}/': 'Detalhes de um áudio',
            'PUT /api/audio/{id}/': 'Atualiza um áudio',
            'DELETE /api/audio/{id}/': 'Deleta um áudio',
            
            'GET /api/transcriptions/': 'Lista todas as cifras do usuário',
            'POST /api/transcriptions/': 'Cria uma nova cifra',
            'GET /api/transcriptions/{id}/': 'Detalhes de uma cifra',
            'PUT /api/transcriptions/{id}/': 'Atualiza uma cifra',
            'DELETE /api/transcriptions/{id}/': 'Deleta uma cifra',
            
            'GET /api/playlists/': 'Lista playlists do usuário',
            'POST /api/playlists/': 'Cria nova playlist',
            'POST /api/playlists/{id}/add_transcription/': 'Adiciona cifra à playlist',
            'POST /api/playlists/{id}/remove_transcription/': 'Remove cifra da playlist',
            
            'GET /api/jobs/': 'Lista jobs de processamento',
            'GET /api/jobs/{id}/status/': 'Status de um job',
        }
    })

@api_view(['GET'])
def debug_view(request):
    """
    Endpoint de debug - informações sobre o servidor e requisição
    Apenas em desenvolvimento
    """
    from django.conf import settings
    
    return Response({
        'message': 'Debug Info - API DECIFRAE',
        'debug_mode': settings.DEBUG,
        'allowed_hosts': settings.ALLOWED_HOSTS,
        'request_info': {
            'method': request.method,
            'path': request.path,
            'host': request.get_host(),
            'user': str(request.user),
            'is_authenticated': request.user.is_authenticated,
            'headers': {
                'Content-Type': request.META.get('CONTENT_TYPE', 'N/A'),
                'Authorization': 'SET' if request.META.get('HTTP_AUTHORIZATION') else 'NOT SET',
                'X-Forwarded-Proto': request.META.get('HTTP_X_FORWARDED_PROTO', 'N/A'),
                'X-Forwarded-Host': request.META.get('HTTP_X_FORWARDED_HOST', 'N/A'),
            }
        },
        'supabase_config': {
            'url_set': bool(os.environ.get('SUPABASE_URL')),
            'storage_bucket': os.environ.get('SUPABASE_STORAGE_BUCKET', 'audio-files'),
        }
    })