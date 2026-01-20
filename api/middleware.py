"""
Middleware para autenticação com Supabase
"""
from django.contrib.auth.models import User, AnonymousUser
from django.http import JsonResponse
from django.utils.decorators import sync_and_async_middleware
from api.supabase_client import supabase_client
import logging

logger = logging.getLogger(__name__)


class SupabaseAuthMiddleware:
    """
    Middleware para autenticar usuários via token JWT do Supabase.
    Valida o token contra a API de Auth do Supabase e cria/atualiza o usuário no Django.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Tenta autenticar com o Supabase
        self._authenticate_request(request)
        
        response = self.get_response(request)
        return response

    def _authenticate_request(self, request):
        """
        Extrai o token JWT do header Authorization e valida com Supabase.
        """
        auth_header = request.headers.get('Authorization', '')
        
        # Se não há header Authorization, mantém como anônimo
        if not auth_header:
            request.user = AnonymousUser()
            request.supabase_user = None
            return
        
        # Extrai o token do header
        if not auth_header.startswith('Bearer '):
            request.user = AnonymousUser()
            request.supabase_user = None
            return
        
        token = auth_header.split(' ')[1].strip()
        
        try:
            # Verifica o token no Supabase Auth
            supabase_user = supabase_client.verify_user_token(token)
            
            if not supabase_user or not hasattr(supabase_user, 'user'):
                request.user = AnonymousUser()
                request.supabase_user = None
                return
            
            # Extrai dados do usuário
            supabase_user_id = supabase_user.user.id
            email = supabase_user.user.email
            user_metadata = supabase_user.user.user_metadata or {}
            
            # Busca ou cria o usuário no Django
            # Usa o email como username para garantir unicidade
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],  # Usa parte do email como username
                    'first_name': user_metadata.get('name', email.split('@')[0]),
                }
            )
            
            # Se o usuário já existia, atualiza seus dados
            if not created:
                user.first_name = user_metadata.get('name', user.first_name)
                user.save(update_fields=['first_name'])
            
            # Armazena o usuário e dados do Supabase na request
            request.user = user
            request.supabase_user = supabase_user
            request.supabase_user_id = supabase_user_id
            
            logger.debug(f"Usuário autenticado via Supabase: {email}")
            
        except Exception as e:
            # Log do erro para debug
            logger.warning(f"Erro ao validar token Supabase: {str(e)}")
            
            # Se o token é inválido, mantém como anônimo
            request.user = AnonymousUser()
            request.supabase_user = None
            request.supabase_user_id = None
