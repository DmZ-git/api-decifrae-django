from rest_framework import serializers
from .models import AudioFile, Transcription, Playlist, ProcessingJob


class AudioFileSerializer(serializers.ModelSerializer):
    """
    Serializador para o modelo AudioFile
    """
    class Meta:
        model = AudioFile
        fields = ['id', 'user', 'title', 'file_url', 'file_name', 'file_size', 'duration', 'format', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def validate_title(self, value):
        if not value.strip():
            raise serializers.ValidationError("O título não pode ser vazio.")
        return value


class TranscriptionSerializer(serializers.ModelSerializer):
    """
    Serializador para o modelo Transcription
    """
    audio_file_title = serializers.CharField(source='audio_file.title', read_only=True)
    
    class Meta:
        model = Transcription
        fields = ['id', 'audio_file', 'audio_file_title', 'user', 'title', 'artist', 'chords', 'lyrics', 
                  'key', 'bpm', 'tempo_map', 'confidence', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def validate_bpm(self, value):
        if value is not None and (value < 20 or value > 300):
            raise serializers.ValidationError("BPM deve estar entre 20 e 300.")
        return value

    def validate_confidence(self, value):
        if value is not None and (value < 0 or value > 1):
            raise serializers.ValidationError("Confiança deve estar entre 0 e 1.")
        return value


class PlaylistSerializer(serializers.ModelSerializer):
    """
    Serializador para o modelo Playlist
    """
    transcription_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Playlist
        fields = ['id', 'user', 'name', 'description', 'transcriptions', 'transcription_count', 
                  'is_public', 'cover_image_url', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def get_transcription_count(self, obj):
        return obj.transcriptions.count()

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("O nome da playlist não pode ser vazio.")
        return value


class ProcessingJobSerializer(serializers.ModelSerializer):
    """
    Serializador para o modelo ProcessingJob
    """
    audio_file_title = serializers.CharField(source='audio_file.title', read_only=True)
    
    class Meta:
        model = ProcessingJob
        fields = ['id', 'audio_file', 'audio_file_title', 'job_type', 'status', 'progress', 
                  'parameters', 'result', 'error_message', 'celery_task_id', 
                  'started_at', 'completed_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'status', 'progress', 'result', 'error_message', 'celery_task_id', 
                           'started_at', 'completed_at', 'created_at', 'updated_at']

    def validate_progress(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Progresso deve estar entre 0 e 100.")
        return value
