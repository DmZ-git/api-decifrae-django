from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from .models import AudioFile, Transcription, Playlist, ProcessingJob


class AudioFileModelTest(TestCase):
    """
    Testes para o modelo AudioFile
    """
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.audio = AudioFile.objects.create(
            user=self.user,
            title='Teste Audio',
            file_url='https://supabase.co/audio/test.mp3',
            file_name='test.mp3',
            file_size=1024000,
            format='mp3'
        )

    def test_audio_creation(self):
        """Testa a criação de um áudio"""
        self.assertEqual(self.audio.title, 'Teste Audio')
        self.assertEqual(self.audio.status, 'uploaded')
        self.assertEqual(self.audio.user, self.user)

    def test_audio_str(self):
        """Testa a representação string do áudio"""
        self.assertEqual(str(self.audio), 'Teste Audio (test.mp3)')


class TranscriptionModelTest(TestCase):
    """
    Testes para o modelo Transcription
    """
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.audio = AudioFile.objects.create(
            user=self.user,
            title='Audio Teste',
            file_url='https://test.com/audio.mp3',
            file_name='audio.mp3',
            format='mp3'
        )
        self.transcription = Transcription.objects.create(
            audio_file=self.audio,
            user=self.user,
            title='Música Teste',
            artist='Artista Teste',
            chords=['C', 'G', 'Am', 'F'],
            key='C',
            bpm=120
        )

    def test_transcription_creation(self):
        """Testa a criação de uma transcrição"""
        self.assertEqual(self.transcription.title, 'Música Teste')
        self.assertEqual(self.transcription.bpm, 120)
        self.assertEqual(self.transcription.key, 'C')


class PlaylistModelTest(TestCase):
    """
    Testes para o modelo Playlist
    """
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.playlist = Playlist.objects.create(
            user=self.user,
            name='Minhas Favoritas',
            description='Playlist de teste',
            is_public=False
        )

    def test_playlist_creation(self):
        """Testa a criação de uma playlist"""
        self.assertEqual(self.playlist.name, 'Minhas Favoritas')
        self.assertEqual(self.playlist.user, self.user)
        self.assertFalse(self.playlist.is_public)

    def test_playlist_add_transcription(self):
        """Testa adicionar transcrição à playlist"""
        audio = AudioFile.objects.create(
            user=self.user,
            title='Audio',
            file_url='https://test.com/audio.mp3',
            file_name='audio.mp3',
            format='mp3'
        )
        transcription = Transcription.objects.create(
            audio_file=audio,
            user=self.user,
            title='Música',
            chords=['C', 'G']
        )
        self.playlist.transcriptions.add(transcription)
        self.assertEqual(self.playlist.transcriptions.count(), 1)


class ProcessingJobModelTest(TestCase):
    """
    Testes para o modelo ProcessingJob
    """
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.audio = AudioFile.objects.create(
            user=self.user,
            title='Audio Teste',
            file_url='https://test.com/audio.mp3',
            file_name='audio.mp3',
            format='mp3'
        )
        self.job = ProcessingJob.objects.create(
            audio_file=self.audio,
            job_type='chord_detection',
            status='pending'
        )

    def test_job_creation(self):
        """Testa a criação de um job"""
        self.assertEqual(self.job.job_type, 'chord_detection')
        self.assertEqual(self.job.status, 'pending')
        self.assertEqual(self.job.progress, 0)


class APITestCase(APITestCase):
    """
    Testes para os endpoints da API
    """
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client.force_authenticate(user=self.user)

    def test_audio_list(self):
        """Testa listagem de áudios"""
        AudioFile.objects.create(
            user=self.user,
            title='Audio 1',
            file_url='https://test.com/audio1.mp3',
            file_name='audio1.mp3',
            format='mp3'
        )
        response = self.client.get('/api/audio/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_playlist_create(self):
        """Testa criação de playlist"""
        data = {
            'name': 'Nova Playlist',
            'description': 'Descrição',
            'is_public': False
        }
        response = self.client.post('/api/playlists/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Nova Playlist')
