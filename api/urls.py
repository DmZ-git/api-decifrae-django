from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'audio', views.AudioFileViewSet, basename='audiofile')
router.register(r'transcriptions', views.TranscriptionViewSet, basename='transcription')
router.register(r'playlists', views.PlaylistViewSet, basename='playlist')
router.register(r'jobs', views.ProcessingJobViewSet, basename='processingjob')

urlpatterns = [
    path('', views.home, name='home'),
    path('help/', views.help_view, name='help'),
    path('', include(router.urls)),
]
