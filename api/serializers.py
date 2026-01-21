from rest_framework import serializers
from .models import AudioFile, Transcription, ProcessingJob


class AudioFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioFile
        fields = ['id', 'user', 'title', 'file_url', 'file_name', 'file_size', 'duration', 'format', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class TranscriptionSerializer(serializers.ModelSerializer):
    audio_file_title = serializers.CharField(source='audio_file.title', read_only=True)
    
    class Meta:
        model = Transcription
        fields = ['id', 'audio_file', 'audio_file_title', 'user', 'title', 'artist', 'chords', 'lyrics', 
                  'key', 'bpm', 'tempo_map', 'confidence', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class ProcessingJobSerializer(serializers.ModelSerializer):
    audio_file_title = serializers.CharField(source='audio_file.title', read_only=True)
    
    class Meta:
        model = ProcessingJob
        fields = ['id', 'audio_file', 'audio_file_title', 'job_type', 'status', 'progress', 
                  'parameters', 'result', 'error_message', 'celery_task_id', 
                  'started_at', 'completed_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
