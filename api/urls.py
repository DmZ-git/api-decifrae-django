from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'audio', views.AudioFileViewSet, basename='audiofile')
router.register(r'transcriptions', views.TranscriptionViewSet, basename='transcription')
router.register(r'playlists', views.PlaylistViewSet, basename='playlist')
router.register(r'jobs', views.ProcessingJobViewSet, basename='processingjob')

urlpatterns = [
    # Rotas principais
    path('', views.home, name='home'),
    path('help/', views.help_view, name='help'),
    path('debug/', views.debug_view, name='debug'),
    
    # Rota de autenticação (apenas para obter dados do usuário)
    path('auth/me/', views.me_view, name='me'),
    
    # Rotas do router
    path('', include(router.urls)),
]
