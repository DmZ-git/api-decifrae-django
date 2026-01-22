from rest_framework import serializers
from .models import AudioFile, Transcription, ProcessingJob, Playlist


class AudioFileSerializer(serializers.ModelSerializer):
    filename = serializers.CharField(source='file_name', read_only=True)

    class Meta:
        model = AudioFile
        fields = ['id', 'user', 'title', 'file_url', 'file_name', 'filename', 'file_size', 'duration', 'format', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at', 'filename']


class TranscriptionSerializer(serializers.ModelSerializer):
    audio_file_title = serializers.CharField(source='audio_file.title', read_only=True)
    content = serializers.CharField(source='lyrics', required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Transcription
        fields = [
            'id', 'audio_file', 'audio_file_title', 'user', 'title', 'artist',
            'chords', 'content', 'key', 'bpm', 'tempo_map', 'confidence', 'notes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Simplifica chords para array de strings quando armazenado como lista de dicts
        chords_field = data.get('chords') or []
        if isinstance(chords_field, list) and chords_field and isinstance(chords_field[0], dict):
            data['chords'] = [c.get('acorde') for c in chords_field if isinstance(c, dict) and c.get('acorde')]
        return data


class ProcessingJobSerializer(serializers.ModelSerializer):
    audio_file_title = serializers.CharField(source='audio_file.title', read_only=True)
    
    class Meta:
        model = ProcessingJob
        fields = ['id', 'audio_file', 'audio_file_title', 'job_type', 'status', 'progress', 
                  'parameters', 'result', 'error_message', 'celery_task_id', 
                  'started_at', 'completed_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class PlaylistSerializer(serializers.ModelSerializer):
    transcriptions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Transcription.objects.all(), required=False
    )

    class Meta:
        model = Playlist
        fields = [
            'id', 'user', 'name', 'description', 'transcriptions', 'is_public',
            'cover_image_url', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

    def create(self, validated_data):
        transcriptions = validated_data.pop('transcriptions', [])
        playlist = Playlist.objects.create(**validated_data)
        if transcriptions:
            playlist.transcriptions.set(transcriptions)
        return playlist

    def update(self, instance, validated_data):
        transcriptions = validated_data.pop('transcriptions', None)
        instance = super().update(instance, validated_data)
        if transcriptions is not None:
            instance.transcriptions.set(transcriptions)
        return instance
