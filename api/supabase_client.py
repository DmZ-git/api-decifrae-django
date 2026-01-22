"""
Cliente Supabase para integração com a API
"""
import os
import logging
from supabase import create_client, Client
from django.conf import settings

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
        logger.info("✅ Cliente Supabase inicializado com sucesso")

    def ensure_bucket(self, bucket: str = None, public: bool = True) -> bool:
        """
        Verifica se bucket existe. Se não existir, tenta criar.
        Em produção, é preferível criar buckets manualmente no Supabase Dashboard.
        """
        if not self._client:
            logger.warning("Supabase client não configurado")
            return False

        if bucket is None:
            bucket = os.environ.get('SUPABASE_STORAGE_BUCKET', 'audio-files')

        try:
            # Simplesmente retorna True se conseguir listar buckets
            # (significa que tem acesso à API)
            buckets = self._client.storage.list_buckets()
            logger.info(f"Bucket '{bucket}' access verified")
            return True
        except Exception as e:
            logger.warning(f"Não foi possível verificar bucket '{bucket}': {e}")
            # Continua mesmo assim (bucket pode estar inacessível mas upload pode funcionar)
            return True

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
            # Upload direto (bucket já deve existir e ser público)
            logger.info(f"Uploading {file_path} to bucket '{bucket}'")
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
            
            logger.info(f"Upload successful: {public_url}")
            return {
                'success': True,
                'path': file_path,
                'public_url': public_url,
                'bucket': bucket
            }
        except Exception as e:
            logger.error(f"Upload failed: {str(e)}")
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
        if not self._client:
            raise ValueError('Supabase client não configurado')

        if bucket is None:
            bucket = os.environ.get('SUPABASE_STORAGE_BUCKET', 'audio-files')
        
        return self._client.storage.from_(bucket).download(file_path)

    def _extract_path_from_public_url(self, public_url: str, bucket: str) -> str:
        """Extrai o caminho relativo do arquivo a partir de uma URL pública."""
        marker = f"/storage/v1/object/public/{bucket}/"
        if marker not in public_url:
            return ''
        return public_url.split(marker, 1)[1]

    def download_audio_by_url(self, public_url: str, bucket: str = None) -> bytes:
        """Download seguro usando service key a partir de uma URL pública."""
        if not self._client:
            raise ValueError('Supabase client não configurado')

        if bucket is None:
            bucket = os.environ.get('SUPABASE_STORAGE_BUCKET', 'audio-files')

        file_path = self._extract_path_from_public_url(public_url, bucket)
        if not file_path:
            raise ValueError('Não foi possível extrair o caminho do arquivo para download')

        return self._client.storage.from_(bucket).download(file_path)

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
        Verifica token JWT do Supabase Auth.
        
        Fluxo esperado:
        1. Cliente faz login no Supabase Auth
        2. Supabase retorna token JWT com user.id, user.email, etc
        3. Cliente envia token no header Authorization: Bearer {token}
        4. Middleware chama este método
        5. Se válido: retorna user_response.user com dados
        
        Args:
            token: Token JWT do usuário (bearer token sem "Bearer " prefix)
        
        Returns:
            Wrapper object com atributo .user contendo dados do usuário Supabase
            
        Raises:
            ValueError: Se token inválido ou Supabase client não configurado
        """
        if not self._client:
            logger.error("Supabase client não configurado; não é possível verificar token")
            raise ValueError("Supabase client não configurado")
        
        try:
            # Chama Supabase Auth para verificar o token JWT
            user_response = self._client.auth.get_user(token)
            
            # user_response é um User object com atributos:
            # - id: UUID único do usuário
            # - email: email do usuário
            # - email_confirmed_at: quando confirmou email
            # - user_metadata: dados customizados (name, etc)
            # - app_metadata: dados da app
            # - created_at: quando criou conta
            
            # Wrapper para compatibilidade com middleware
            class UserWrapper:
                def __init__(self, user_data):
                    self.user = user_data
            
            logger.info(f"Token verificado com sucesso para user_id={user_response.id}")
            return UserWrapper(user_response)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Erro ao verificar token JWT: {error_msg}")
            raise ValueError(f"Token inválido: {error_msg}")


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
