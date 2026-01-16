from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import AudioFile, Transcription, Playlist, ProcessingJob
from .serializers import AudioFileSerializer, TranscriptionSerializer, PlaylistSerializer, ProcessingJobSerializer
from .supabase_client import SupabaseClient
import uuid
import os


@method_decorator(csrf_exempt, name='dispatch')
class AudioFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operações CRUD de AudioFile
    """
    queryset = AudioFile.objects.all()
    serializer_class = AudioFileSerializer
    permission_classes = [AllowAny]  # Permitir acesso sem autenticação para testes
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        # Se usuário estiver autenticado, retorna apenas seus áudios
        if self.request.user.is_authenticated:
            return AudioFile.objects.filter(user=self.request.user)
        # Caso contrário, retorna todos (para testes)
        return AudioFile.objects.all()

    def create(self, request, *args, **kwargs):
        """
        Upload de arquivo de áudio com integração Supabase
        """
        file = request.FILES.get('file')
        title = request.data.get('title', 'Sem título')
        
        if not file:
            return Response(
                {'error': 'Nenhum arquivo foi enviado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Gera um nome único para o arquivo
            file_ext = os.path.splitext(file.name)[1]
            unique_filename = f"{uuid.uuid4()}{file_ext}"
            file_path = f"{unique_filename}"
            
            # Faz upload para o Supabase Storage
            supabase_client = SupabaseClient()
            file_content = file.read()
            upload_result = supabase_client.upload_audio(
                file_path=file_path,
                file_content=file_content,
                bucket=os.environ.get('SUPABASE_STORAGE_BUCKET', 'audio-files')
            )
            
            if not upload_result.get('success'):
                return Response(
                    {'error': f'Erro ao fazer upload para o Supabase: {upload_result.get("error")}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Obtém o user_id do Supabase (do token)
            user_id = None
            if hasattr(request, 'supabase_user'):
                user_id = request.supabase_user.user.id
            
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
                    # Retorna o registro do Supabase
                    return Response(supabase_record['data'], status=status.HTTP_201_CREATED)
            
            # Fallback: Cria o registro no banco de dados local
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
            return Response(
                {'error': f'Erro ao processar upload: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        # Associa o arquivo ao usuário logado se autenticado
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()


class TranscriptionViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operações CRUD de Transcription (Cifras)
    """
    queryset = Transcription.objects.all()
    serializer_class = TranscriptionSerializer
    permission_classes = [AllowAny]  # Permitir acesso sem autenticação para testes

    def get_queryset(self):
        # Se usuário estiver autenticado, retorna apenas suas transcrições
        if self.request.user.is_authenticated:
            return Transcription.objects.filter(user=self.request.user)
        return Transcription.objects.all()

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()


class PlaylistViewSet(viewsets.ModelViewSet):
    """
    ViewSet para operações CRUD de Playlist
    """
    queryset = Playlist.objects.all()
    serializer_class = PlaylistSerializer
    permission_classes = [AllowAny]  # Permitir acesso sem autenticação para testes

    def get_queryset(self):
        # Retorna playlists do usuário + públicas de outros
        if self.request.user.is_authenticated:
            return Playlist.objects.filter(user=self.request.user) | Playlist.objects.filter(is_public=True)
        return Playlist.objects.filter(is_public=True)

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
    permission_classes = [AllowAny]  # Permitir acesso sem autenticação para testes

    def get_queryset(self):
        # Retorna jobs dos áudios do usuário se autenticado
        if self.request.user.is_authenticated:
            return ProcessingJob.objects.filter(audio_file__user=self.request.user)
        return ProcessingJob.objects.all()

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
