import logging

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.conf import settings

from .models import AudioFile, Transcription, ProcessingJob, Playlist
from .serializers import (
    AudioFileSerializer,
    TranscriptionSerializer,
    ProcessingJobSerializer,
    PlaylistSerializer
)
from .tasks import processar_audio_async

logger = logging.getLogger(__name__)


class AudioFileViewSet(viewsets.ModelViewSet):
    """
    Representa um áudio enviado pelo usuário (arquivo já existente no Supabase).
    """
    queryset = AudioFile.objects.all()
    serializer_class = AudioFileSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return AudioFile.objects.filter(user=self.request.user)
        return AudioFile.objects.all()

    def create(self, request, *args, **kwargs):
        """
        Cria apenas o REGISTRO do áudio.
        O upload já foi feito no frontend (Supabase Storage).
        """
        audio_path = request.data.get("audio_path")
        title = request.data.get("title", "Sem título")

        if not audio_path:
            return Response(
                {"error": "audio_path é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST
            )

        audio = AudioFile.objects.create(
            user=request.user if request.user.is_authenticated else None,
            title=title,
            file_path=audio_path,
            status="uploaded"
        )

        return Response(
            AudioFileSerializer(audio).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        """
        Dispara o processamento ASSÍNCRONO do áudio.

        POST /api/audio/{id}/process/
        """
        audio_file = self.get_object()

        # Evita processamento duplicado
        if audio_file.status in ("processing", "done"):
            return Response(
                {"error": "Este áudio já está em processamento ou concluído"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cria job de rastreamento (opcional, mas útil)
        job = ProcessingJob.objects.create(
            audio_file=audio_file,
            job_type="chord_detection",
            status="queued",
            progress=0
        )

        try:
            task = processar_audio_async.delay(
                audio_file_id=audio_file.id
            )

            job.celery_task_id = task.id
            job.status = "processing"
            job.progress = 10
            job.save()

            audio_file.status = "processing"
            audio_file.save()

            return Response(
                {
                    "success": True,
                    "message": "Processamento iniciado",
                    "job_id": job.id,
                    "task_id": task.id,
                },
                status=status.HTTP_202_ACCEPTED
            )

        except Exception as e:
            logger.exception("Erro ao iniciar processamento")

            job.status = "failed"
            job.error_message = str(e)
            job.save()

            audio_file.status = "failed"
            audio_file.save()

            return Response(
                {"error": "Falha ao iniciar processamento"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TranscriptionViewSet(viewsets.ModelViewSet):
    """
    Resultado do processamento (cifra + timestamps).
    """
    queryset = Transcription.objects.all()
    serializer_class = TranscriptionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Transcription.objects.filter(user=self.request.user)
        return Transcription.objects.all()
    
class ProcessingJobViewSet(viewsets.ModelViewSet):
    queryset = ProcessingJob.objects.all()
    serializer_class = ProcessingJobSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        job = self.get_object()
        return Response({
            "status": job.status,
            "progress": job.progress,
            "error_message": job.error_message
        })
    
class PlaylistViewSet(viewsets.ModelViewSet):
    queryset = Playlist.objects.all()
    serializer_class = PlaylistSerializer
    permission_classes = [AllowAny]

    @action(detail=True, methods=["post"])
    def add_transcription(self, request, pk=None):
        transcription_id = request.data.get("transcription_id")
        if not transcription_id:
            return Response(
                {"error": "transcription_id é obrigatório"},
                status=status.HTTP_400_BAD_REQUEST
            )

        transcription = Transcription.objects.get(id=transcription_id)
        playlist = self.get_object()
        playlist.transcriptions.add(transcription)

        return Response({"success": True})
