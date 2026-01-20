from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .models import AudioFile, Transcription, Playlist, ProcessingJob
from .serializers import (
    AudioFileSerializer, TranscriptionSerializer, PlaylistSerializer, 
    ProcessingJobSerializer, LoginSerializer, SignUpSerializer, 
    UserSerializer, AuthResponseSerializer
)
from .supabase_client import SupabaseClient
import uuid
import os


# ==========================================
# Endpoints de Autenticação
# ==========================================

@api_view(['POST'])
@csrf_exempt
def login_view(request):
    """
    Endpoint para login do usuário
    
    POST /api/auth/login/
    {
        "email": "user@example.com",
        "password": "password123"
    }
    """
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {
                'success': False,
                'error': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    email = serializer.validated_data['email']
    password = serializer.validated_data['password']

    try:
        # Procura usuário por email
        user = User.objects.get(email=email)
        
        # Autentica com username e senha
        authenticated_user = authenticate(username=user.username, password=password)
        
        if authenticated_user is None:
            return Response(
                {
                    'success': False,
                    'error': 'Email ou senha inválidos'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Gera token de sessão
        from django.contrib.auth.models import update_last_login
        from rest_framework.authtoken.models import Token
        
        # Cria ou obter token
        token, _ = Token.objects.get_or_create(user=authenticated_user)
        update_last_login(None, authenticated_user)
        
        user_serializer = UserSerializer(authenticated_user)
        
        return Response(
            {
                'success': True,
                'message': 'Login realizado com sucesso',
                'user': user_serializer.data,
                'token': token.key,
                'expires_in': 3600  # 1 hora
            },
            status=status.HTTP_200_OK
        )
        
    except User.DoesNotExist:
        return Response(
            {
                'success': False,
                'error': 'Email ou senha inválidos'
            },
            status=status.HTTP_401_UNAUTHORIZED
        )
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Erro ao fazer login: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@csrf_exempt
def signup_view(request):
    """
    Endpoint para criar nova conta
    
    POST /api/auth/signup/
    {
        "email": "newuser@example.com",
        "password": "securepassword123",
        "password_confirm": "securepassword123",
        "first_name": "João",
        "last_name": "Silva"
    }
    """
    serializer = SignUpSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {
                'success': False,
                'error': serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        first_name = serializer.validated_data.get('first_name', '')
        last_name = serializer.validated_data.get('last_name', '')

        # Cria novo usuário
        username = email.split('@')[0]  # Usa email como base
        
        # Se username existe, adiciona números
        if User.objects.filter(username=username).exists():
            counter = 1
            while User.objects.filter(username=f"{username}{counter}").exists():
                counter += 1
            username = f"{username}{counter}"

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Gera token
        from rest_framework.authtoken.models import Token
        token, _ = Token.objects.get_or_create(user=user)
        
        user_serializer = UserSerializer(user)
        
        return Response(
            {
                'success': True,
                'message': 'Conta criada com sucesso',
                'user': user_serializer.data,
                'token': token.key,
                'expires_in': 3600
            },
            status=status.HTTP_201_CREATED
        )
        
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Erro ao criar conta: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def logout_view(request):
    """
    Endpoint para logout do usuário
    
    POST /api/auth/logout/
    Headers: Authorization: Token YOUR_TOKEN
    """
    try:
        if not request.user.is_authenticated:
            return Response(
                {
                    'success': False,
                    'error': 'Usuário não autenticado'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Remove token
        from rest_framework.authtoken.models import Token
        try:
            token = Token.objects.get(user=request.user)
            token.delete()
        except Token.DoesNotExist:
            pass
        
        return Response(
            {
                'success': True,
                'message': 'Logout realizado com sucesso'
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response(
            {
                'success': False,
                'error': f'Erro ao fazer logout: {str(e)}'
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
def me_view(request):
    """
    Endpoint para obter dados do usuário autenticado
    
    GET /api/auth/me/
    Headers: Authorization: Token YOUR_TOKEN
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


@api_view(['POST'])
def verify_token_view(request):
    """
    Endpoint para verificar se um token é válido
    
    POST /api/auth/verify-token/
    {
        "token": "YOUR_TOKEN"
    }
    """
    token = request.data.get('token')
    
    if not token:
        return Response(
            {
                'success': False,
                'error': 'Token não fornecido'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        from rest_framework.authtoken.models import Token
        token_obj = Token.objects.get(key=token)
        user_serializer = UserSerializer(token_obj.user)
        
        return Response(
            {
                'success': True,
                'valid': True,
                'user': user_serializer.data
            },
            status=status.HTTP_200_OK
        )
    except Token.DoesNotExist:
        return Response(
            {
                'success': False,
                'valid': False,
                'error': 'Token inválido'
            },
            status=status.HTTP_401_UNAUTHORIZED
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
                user=request.user,  # Sempre usa o usuário autenticado
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
