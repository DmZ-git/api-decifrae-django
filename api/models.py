from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class AudioFile(models.Model):
    STATUS_CHOICES = [
        ("uploaded", "Enviado"),
        ("processing", "Processando"),
        ("completed", "Concluído"),
        ("failed", "Falhou"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="audio_files",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=255)

    # URL pública no Supabase Storage
    file_url = models.URLField(max_length=500)

    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    format = models.CharField(max_length=10)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="uploaded",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "audio_files"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.file_name})"


class Transcription(models.Model):
    audio_file = models.ForeignKey(
        AudioFile,
        on_delete=models.CASCADE,
        related_name="transcriptions",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=255)

    # JSON FINAL PADRÃO DA CIFRA
    # {
    #   "chords": ["C", "G", "Am"],
    #   "content": "[Intro]\nC G Am",
    #   "timestamps": [
    #       { "start": 0.0, "end": 2.5, "chord": "C" }
    #   ]
    # }
    data = models.JSONField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "transcriptions"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

class ProcessingJob(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pendente"),
        ("processing", "Processando"),
        ("completed", "Concluído"),
        ("failed", "Falhou"),
    ]

    audio_file = models.ForeignKey(
        AudioFile,
        on_delete=models.CASCADE,
        related_name="processing_jobs",
    )

    job_type = models.CharField(
        max_length=50,
        default="chord_detection",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    progress = models.IntegerField(default=0)

    # dados auxiliares
    parameters = models.JSONField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    celery_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "processing_jobs"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.status == "processing" and not self.started_at:
            self.started_at = timezone.now()
        if self.status in ("completed", "failed") and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Job {self.id} - {self.status}"


class Playlist(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="playlists",
    )

    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)

    transcriptions = models.ManyToManyField(
        Transcription,
        related_name="playlists",
        blank=True,
    )

    is_public = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "playlists"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
