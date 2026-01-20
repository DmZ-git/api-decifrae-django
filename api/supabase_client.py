"""
Cliente Supabase para integração com a API
"""
import os
from supabase import create_client, Client
from django.conf import settings
import jwt
from jwt import PyJWKClient
import logging

logger = logging.getLogger(__name__)


class SupabaseClient:
    """
    Classe singleton para gerenciar a conexão com o Supabase
    """
    _instance = None
    _client: Client = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """
        Inicializa o cliente Supabase
        """
        supabase_url = os.environ.get('SUPABASE_URL')
        # Usa service_role key para operações do backend
        supabase_key = os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            logger.warning("⚠️  SUPABASE_URL e SUPABASE_SERVICE_KEY não configurados. Funcionalidades de storage desabilitadas.")
            self._client = None
            return
        
        self._client = create_client(supabase_url, supabase_key)

    @property
    def client(self) -> Client:
        """
        Retorna a instância do cliente Supabase
        """
        return self._client

    def upload_audio(self, file_path: str, file_content: bytes, bucket: str = None) -> dict:
        """
        Upload de arquivo de áudio para o Supabase Storage
        
        Args:
            file_path: Caminho/nome do arquivo no bucket
            file_content: Conteúdo do arquivo em bytes
            bucket: Nome do bucket (padrão: audio-files)
        
        Returns:
            dict com 'success', 'path', 'public_url' do arquivo
        """
        if not self._client:
            return {
                'success': False,
                'error': 'Supabase client não configurado'
            }
            
        if bucket is None:
            bucket = os.environ.get('SUPABASE_STORAGE_BUCKET', 'audio-files')
        
        try:
            # Upload do arquivo com upsert=True para sobrescrever se existir
            response = self._client.storage.from_(bucket).upload(
                path=file_path,
                file=file_content,
                file_options={
                    "content-type": "audio/mpeg",
                    "upsert": "true"
                }
            )
            
            # Obtém a URL pública
            public_url = self._client.storage.from_(bucket).get_public_url(file_path)
            
            return {
                'success': True,
                'path': file_path,
                'public_url': public_url,
                'bucket': bucket
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def download_audio(self, file_path: str, bucket: str = None) -> bytes:
        """
        Download de arquivo de áudio do Supabase Storage
        
        Args:
            file_path: Caminho do arquivo no bucket
            bucket: Nome do bucket (padrão: audio-files)
        
        Returns:
            bytes: Conteúdo do arquivo
        """
        if bucket is None:
            bucket = os.environ.get('SUPABASE_STORAGE_BUCKET', 'audio-files')
        
        response = self._client.storage.from_(bucket).download(file_path)
        return response

    def delete_audio(self, file_path: str, bucket: str = None) -> bool:
        """
        Deleta arquivo de áudio do Supabase Storage
        
        Args:
            file_path: Caminho do arquivo no bucket
            bucket: Nome do bucket (padrão: audio-files)
        
        Returns:
            bool: True se deletado com sucesso
        """
        if bucket is None:
            bucket = os.environ.get('SUPABASE_STORAGE_BUCKET', 'audio-files')
        
        response = self._client.storage.from_(bucket).remove([file_path])
        return len(response) > 0

    def get_public_url(self, file_path: str, bucket: str = None) -> str:
        """
        Obtém a URL pública de um arquivo
        
        Args:
            file_path: Caminho do arquivo no bucket
            bucket: Nome do bucket (padrão: audio-files)
        
        Returns:
            str: URL pública do arquivo
        """
        if bucket is None:
            bucket = os.environ.get('SUPABASE_STORAGE_BUCKET', 'audio-files')
        
        return self._client.storage.from_(bucket).get_public_url(file_path)

    def verify_user_token(self, token: str):
        """
        Verifica token JWT do Supabase Auth usando PyJWT
        
        Args:
            token: Token JWT do usuário
        
        Returns:
            objeto com user e outros dados se válido
        """
        try:
            supabase_url = os.environ.get('SUPABASE_URL')
            if not supabase_url:
                raise ValueError("SUPABASE_URL não configurado")
            
            # Extrai project_ref da URL (ex: https://xxxxx.supabase.co -> xxxxx)
            project_ref = supabase_url.split('//')[1].split('.')[0]
            jwks_url = f"https://{project_ref}.supabase.co/auth/v1/jwks"
            
            # Carrega as chaves públicas do Supabase
            jwks_client = PyJWKClient(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            
            # Decodifica e valida o token
            decoded = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience="authenticated",
                options={"verify_aud": True}
            )
            
            # Cria um objeto similar ao que o frontend espera
            class UserData:
                def __init__(self, decoded_token):
                    self.user = type('obj', (object,), {
                        'id': decoded_token.get('sub'),
                        'email': decoded_token.get('email'),
                        'user_metadata': decoded_token.get('user_metadata', {})
                    })()
            
            return UserData(decoded)
            
        except jwt.ExpiredSignatureError:
            logger.warning(f"Token expirado")
            raise ValueError("Token expirado")
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token inválido: {str(e)}")
            raise ValueError(f"Token inválido: {str(e)}")
        except Exception as e:
            logger.error(f"Erro ao verificar token: {str(e)}")
            raise ValueError(f"Erro ao verificar token: {str(e)}")

    def create_audio_file(self, audio_data: dict) -> dict:
        """
        Cria registro na tabela audio_files do Supabase
        
        Args:
            audio_data: dict com user_id, title, file_path, storage_url, etc.
        
        Returns:
            dict com 'success' e 'data' ou 'error'
        """
        if not self._client:
            return {
                'success': False,
                'error': 'Supabase client não configurado'
            }
        
        try:
            response = self._client.table('audio_files').insert(audio_data).execute()
            return {
                'success': True,
                'data': response.data[0] if response.data else None
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def list_files(self, path: str = "", bucket: str = None) -> list:
        """
        Lista arquivos no bucket
        
        Args:
            path: Caminho no bucket (vazio para raiz)
            bucket: Nome do bucket (padrão: audio-files)
        
        Returns:
            list: Lista de arquivos
        """
        if bucket is None:
            bucket = os.environ.get('SUPABASE_STORAGE_BUCKET', 'audio-files')
        
        response = self._client.storage.from_(bucket).list(path)
        return response


# Instância global do cliente
supabase_client = SupabaseClient()


# Funções auxiliares para uso direto
def upload_audio_file(file_path: str, file_content: bytes) -> dict:
    """Atalho para upload de áudio"""
    return supabase_client.upload_audio(file_path, file_content)


def download_audio_file(file_path: str) -> bytes:
    """Atalho para download de áudio"""
    return supabase_client.download_audio(file_path)


def get_audio_url(file_path: str) -> str:
    """Atalho para obter URL do áudio"""
    return supabase_client.get_public_url(file_path)


def delete_audio_file(file_path: str) -> bool:
    """Atalho para deletar áudio"""
    return supabase_client.delete_audio(file_path)
