from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'audio', views.AudioFileViewSet, basename='audiofile')
router.register(r'transcriptions', views.TranscriptionViewSet, basename='transcription')
router.register(r'jobs', views.ProcessingJobViewSet, basename='processingjob')
router.register(r'playlists', views.PlaylistViewSet, basename='playlist')

urlpatterns = [
    path('', include(router.urls)),
]
