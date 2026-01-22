"""
Middleware para autenticação com Supabase
"""
import logging
from django.contrib.auth.models import User
from django.http import JsonResponse
from api.supabase_client import supabase_client

logger = logging.getLogger(__name__)


class SupabaseAuthMiddleware:
    """
    Middleware para autenticar usuários via token do Supabase.
    
    Fluxo:
    1. Cliente (React/Vercel) faz login no Supabase → recebe token JWT
    2. Cliente envia Authorization: Bearer {token} em requisições
    3. Middleware valida token com Supabase Auth
    4. Se válido: sincroniza usuário no Django + request.user = user_django
    5. Se inválido: request.user = AnonymousUser (AllowAny permite continuação)
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Obtém token do header Authorization: Bearer <token>
        auth_header = request.headers.get('Authorization', '')
        
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            try:
                # Valida token com Supabase Auth
                supabase_user = supabase_client.verify_user_token(token)
                
                # Extrai email e metadata do usuário
                user_email = supabase_user.user.email if hasattr(supabase_user.user, 'email') else None
                user_metadata = supabase_user.user.user_metadata if hasattr(supabase_user.user, 'user_metadata') else {}
                user_id = supabase_user.user.id if hasattr(supabase_user.user, 'id') else None
                
                if not user_email:
                    logger.warning(f"Token válido mas sem email. user_id={user_id}")
                    return self.get_response(request)
                
                # Sincroniza usuário no banco Django (get_or_create)
                user, created = User.objects.get_or_create(
                    username=user_email,
                    defaults={
                        'email': user_email,
                        'first_name': user_metadata.get('name', ''),
                    }
                )
                
                # Anexa dados à request
                request.user = user
                request.supabase_user = supabase_user
                request.supabase_user_id = user_id
                
                logger.debug(f"User autenticado: {user_email} (Django user_id={user.id}, Supabase id={user_id})")
                
            except Exception as e:
                # Token inválido ou erro ao verificar - usuário fica anônimo
                logger.debug(f"Falha na autenticação Supabase: {str(e)}")
                # request.user permanece AnonymousUser
                pass
        
        response = self.get_response(request)
        return response
