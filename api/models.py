from django.db import models
from django.contrib.auth.models import User


class AudioFile(models.Model):
    """
    Modelo para arquivos de áudio enviados pelo usuário
    Armazena metadados e referência ao arquivo no Supabase Storage
    """
    STATUS_CHOICES = [
        ('uploaded', 'Enviado'),
        ('processing', 'Processando'),
        ('completed', 'Completo'),
        ('failed', 'Falhou'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audio_files', verbose_name='Usuário', null=True, blank=True)
    title = models.CharField(max_length=255, verbose_name='Título')
    file_url = models.URLField(max_length=500, verbose_name='URL do Arquivo no Supabase')
    file_name = models.CharField(max_length=255, verbose_name='Nome do Arquivo')
    file_size = models.BigIntegerField(verbose_name='Tamanho (bytes)', null=True, blank=True)
    duration = models.FloatField(null=True, blank=True, verbose_name='Duração (segundos)')
    format = models.CharField(max_length=10, verbose_name='Formato (mp3, wav, etc.)')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded', verbose_name='Status')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Arquivo de Áudio'
        verbose_name_plural = 'Arquivos de Áudio'
        ordering = ['-created_at']
        db_table = 'audio_files'

    def __str__(self):
        return f"{self.title} ({self.file_name})"

    def to_json(self):
        return {
            'id': self.id,
            'user_id': self.user.id if self.user else None,
            'title': self.title,
            'file_url': self.file_url,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'duration': self.duration,
            'format': self.format,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Transcription(models.Model):
    """
    Modelo para cifras (transcrições) geradas a partir dos áudios
    Contém acordes, letra, tom e outras informações musicais
    """
    audio_file = models.ForeignKey(AudioFile, on_delete=models.CASCADE, related_name='transcriptions', verbose_name='Arquivo de Áudio')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transcriptions', verbose_name='Usuário', null=True, blank=True)
    title = models.CharField(max_length=255, verbose_name='Título', help_text='Título da música/cifra')
    artist = models.CharField(max_length=255, blank=True, null=True, verbose_name='Artista')
    
    # Dados musicais extraídos
    chords = models.JSONField(verbose_name='Acordes', help_text='Lista de acordes detectados com timestamps')
    lyrics = models.TextField(blank=True, null=True, verbose_name='Letra', help_text='Letra da música (se disponível)')
    key = models.CharField(max_length=10, blank=True, null=True, verbose_name='Tom', help_text='Tom da música (C, D, Em, etc.)')
    bpm = models.FloatField(null=True, blank=True, verbose_name='BPM', help_text='Batidas por minuto')
    tempo_map = models.JSONField(null=True, blank=True, verbose_name='Mapa de Tempo', help_text='Variações de tempo ao longo da música')
    
    # Metadados
    confidence = models.FloatField(null=True, blank=True, verbose_name='Confiança', help_text='Confiança da detecção (0-1)')
    notes = models.TextField(blank=True, null=True, verbose_name='Notas', help_text='Observações do usuário')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Transcrição/Cifra'
        verbose_name_plural = 'Transcrições/Cifras'
        ordering = ['-created_at']
        db_table = 'transcriptions'

    def __str__(self):
        return f"{self.title} - {self.artist or 'Desconhecido'}"

    def to_json(self):
        return {
            'id': self.id,
            'audio_file_id': self.audio_file.id,
            'user_id': self.user.id if self.user else None,
            'title': self.title,
            'artist': self.artist,
            'chords': self.chords,
            'lyrics': self.lyrics,
            'key': self.key,
            'bpm': self.bpm,
            'tempo_map': self.tempo_map,
            'confidence': self.confidence,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Playlist(models.Model):
    """
    Modelo para playlists de cifras
    Permite ao usuário organizar suas transcrições favoritas
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='playlists', verbose_name='Usuário')
    name = models.CharField(max_length=255, verbose_name='Nome da Playlist')
    description = models.TextField(blank=True, null=True, verbose_name='Descrição')
    transcriptions = models.ManyToManyField(Transcription, related_name='playlists', blank=True, verbose_name='Transcrições')
    is_public = models.BooleanField(default=False, verbose_name='Pública', help_text='Se marcado, outros usuários podem ver esta playlist')
    cover_image_url = models.URLField(max_length=500, blank=True, null=True, verbose_name='URL da Capa')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Playlist'
        verbose_name_plural = 'Playlists'
        ordering = ['-created_at']
        db_table = 'playlists'

    def __str__(self):
        return f"{self.name} - {self.user.username}"

    def to_json(self):
        return {
            'id': self.id,
            'user_id': self.user.id,
            'name': self.name,
            'description': self.description,
            'transcription_ids': list(self.transcriptions.values_list('id', flat=True)),
            'is_public': self.is_public,
            'cover_image_url': self.cover_image_url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ProcessingJob(models.Model):
    """
    Modelo para gerenciar tarefas de processamento de áudio em background
    Rastreia o progresso da análise com librosa
    """
    STATUS_CHOICES = [
        ('pending', 'Pendente'),
        ('processing', 'Processando'),
        ('completed', 'Completo'),
        ('failed', 'Falhou'),
        ('cancelled', 'Cancelado'),
    ]

    audio_file = models.ForeignKey(AudioFile, on_delete=models.CASCADE, related_name='processing_jobs', verbose_name='Arquivo de Áudio')
    job_type = models.CharField(max_length=50, verbose_name='Tipo de Processamento', help_text='Ex: chord_detection, bpm_analysis')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Status')
    progress = models.IntegerField(default=0, verbose_name='Progresso (%)', help_text='0-100')
    
    # Configuração e resultados
    parameters = models.JSONField(null=True, blank=True, verbose_name='Parâmetros', help_text='Parâmetros usados no processamento')
    result = models.JSONField(null=True, blank=True, verbose_name='Resultado', help_text='Resultado do processamento')
    error_message = models.TextField(null=True, blank=True, verbose_name='Mensagem de Erro')
    
    # Rastreamento de tarefa assíncrona
    celery_task_id = models.CharField(max_length=255, null=True, blank=True, verbose_name='ID da Tarefa Celery')
    
    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Iniciado em')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='Completado em')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')

    class Meta:
        verbose_name = 'Job de Processamento'
        verbose_name_plural = 'Jobs de Processamento'
        ordering = ['-created_at']
        db_table = 'processing_jobs'

    def __str__(self):
        return f"Job {self.id}: {self.job_type} - {self.status}"

    def to_json(self):
        return {
            'id': self.id,
            'audio_file_id': self.audio_file.id,
            'job_type': self.job_type,
            'status': self.status,
            'progress': self.progress,
            'parameters': self.parameters,
            'result': self.result,
            'error_message': self.error_message,
            'celery_task_id': self.celery_task_id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
