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
    
    # Rotas de autenticação
    path('auth/login/', views.login_view, name='login'),
    path('auth/signup/', views.signup_view, name='signup'),
    path('auth/logout/', views.logout_view, name='logout'),
    path('auth/me/', views.me_view, name='me'),
    path('auth/verify-token/', views.verify_token_view, name='verify_token'),
    
    # Rotas do router
    path('', include(router.urls)),
]
