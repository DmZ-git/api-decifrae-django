"""
Middleware para autenticação com Supabase
"""
from django.contrib.auth.models import User
from django.http import JsonResponse
from api.supabase_client import supabase_client


class SupabaseAuthMiddleware:
    """
    Middleware para autenticar usuários via token do Supabase
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Obtém o token do header Authorization
        auth_header = request.headers.get('Authorization', '')
        
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            try:
                # Verifica o token no Supabase
                supabase_user = supabase_client.verify_user_token(token)
                
                # Busca ou cria o usuário no Django
                user, created = User.objects.get_or_create(
                    username=supabase_user.user.email,
                    defaults={
                        'email': supabase_user.user.email,
                        'first_name': supabase_user.user.user_metadata.get('name', ''),
                    }
                )
                
                # Associa o usuário à request
                request.user = user
                request.supabase_user = supabase_user
                
            except Exception as e:
                # Token inválido, mantém usuário anônimo
                pass
        
        response = self.get_response(request)
        return response
