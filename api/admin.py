from django.contrib import admin
from .models import AudioFile, Transcription, Playlist, ProcessingJob


@admin.register(AudioFile)
class AudioFileAdmin(admin.ModelAdmin):
    """
    Configuração do Admin para AudioFile
    """
    list_display = ['id', 'title', 'user', 'format', 'duration', 'status', 'created_at']
    list_filter = ['status', 'format', 'created_at']
    search_fields = ['title', 'file_name', 'user__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('user', 'title', 'file_name', 'format')
        }),
        ('Arquivo', {
            'fields': ('file_url', 'file_size', 'duration')
        }),
        ('Status', {
            'fields': ('status',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Transcription)
class TranscriptionAdmin(admin.ModelAdmin):
    """
    Configuração do Admin para Transcription
    """
    list_display = ['id', 'title', 'artist', 'user', 'key', 'bpm', 'confidence', 'created_at']
    list_filter = ['key', 'created_at']
    search_fields = ['title', 'artist', 'user__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Informações da Música', {
            'fields': ('audio_file', 'user', 'title', 'artist')
        }),
        ('Dados Musicais', {
            'fields': ('chords', 'lyrics', 'key', 'bpm', 'tempo_map')
        }),
        ('Metadados', {
            'fields': ('confidence', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    """
    Configuração do Admin para Playlist
    """
    list_display = ['id', 'name', 'user', 'is_public', 'transcription_count', 'created_at']
    list_filter = ['is_public', 'created_at']
    search_fields = ['name', 'description', 'user__username']
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['transcriptions']
    
    def transcription_count(self, obj):
        return obj.transcriptions.count()
    transcription_count.short_description = 'Nº de Cifras'
    
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('user', 'name', 'description', 'cover_image_url')
        }),
        ('Configurações', {
            'fields': ('is_public',)
        }),
        ('Transcrições', {
            'fields': ('transcriptions',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ProcessingJob)
class ProcessingJobAdmin(admin.ModelAdmin):
    """
    Configuração do Admin para ProcessingJob
    """
    list_display = ['id', 'job_type', 'audio_file', 'status', 'progress', 'created_at', 'completed_at']
    list_filter = ['status', 'job_type', 'created_at']
    search_fields = ['audio_file__title', 'job_type', 'celery_task_id']
    ordering = ['-created_at']
    readonly_fields = ['celery_task_id', 'started_at', 'completed_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Job', {
            'fields': ('audio_file', 'job_type', 'status', 'progress')
        }),
        ('Configuração', {
            'fields': ('parameters',)
        }),
        ('Resultado', {
            'fields': ('result', 'error_message')
        }),
        ('Rastreamento', {
            'fields': ('celery_task_id', 'started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
