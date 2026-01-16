"""
Serviço de integração com processador de áudio externo
Este módulo fornece funcionalidades para fazer chamadas a um serviço
de processamento de áudio que roda separadamente
"""

import requests
import os
from typing import Dict, List, Optional


class AudioProcessingService:
    """
    Cliente para comunicar com serviço de processamento de áudio
    
    Pode ser configurado para usar:
    - Serviço local (desenvolvimento)
    - AWS Lambda
    - Google Cloud Functions
    - Serviço custom
    """

    def __init__(self):
        # Configure a URL do seu serviço externo
        self.service_url = os.environ.get(
            'AUDIO_PROCESSING_SERVICE_URL',
            'http://localhost:5000'  # Default para desenvolvimento local
        )
        self.api_key = os.environ.get('AUDIO_PROCESSING_API_KEY', '')
        self.timeout = 300  # 5 minutos para processamento

    def processar_audio(self, file_url: str) -> Optional[Dict]:
        """
        Envia arquivo para processamento em serviço externo
        
        Args:
            file_url: URL do arquivo de áudio (pode ser Supabase, S3, etc)
            
        Returns:
            Dict com resultado do processamento ou None se erro
        """
        try:
            payload = {
                'file_url': file_url,
            }
            
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            response = requests.post(
                f'{self.service_url}/process',
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.ConnectionError:
            return {
                'error': 'Não foi possível conectar ao serviço de processamento',
                'status': 'error'
            }
        except requests.exceptions.Timeout:
            return {
                'error': 'Timeout ao processar áudio',
                'status': 'error'
            }
        except Exception as e:
            return {
                'error': f'Erro ao processar: {str(e)}',
                'status': 'error'
            }

    def classificar_segmento(self, chroma_vector: List[float]) -> Optional[Dict]:
        """
        Classifica um segmento de áudio (chroma vector)
        
        Args:
            chroma_vector: Vetor de 12 notas (chroma)
            
        Returns:
            Dict com classificação do acorde
        """
        try:
            payload = {
                'chroma': chroma_vector,
            }
            
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            response = requests.post(
                f'{self.service_url}/classify',
                json=payload,
                headers=headers,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            return {
                'error': f'Erro ao classificar: {str(e)}',
                'chord': 'Unknown'
            }

    def health_check(self) -> bool:
        """Verifica se serviço está disponível"""
        try:
            response = requests.get(
                f'{self.service_url}/health',
                timeout=5
            )
            return response.status_code == 200
        except:
            return False


# Instância singleton
_audio_service = None


def get_audio_processing_service() -> AudioProcessingService:
    """Factory para obter instância do serviço"""
    global _audio_service
    if _audio_service is None:
        _audio_service = AudioProcessingService()
    return _audio_service
