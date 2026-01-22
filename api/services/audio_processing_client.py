"""
Cliente para processamento de áudio com detecção de acordes
Usa o classificador de acordes central de utils/chord_classifier
para manter a lógica única entre projetos.
"""
import logging
import os
import tempfile
from typing import Dict

import requests

from api.utils import chord_classifier

logger = logging.getLogger(__name__)


class AudioProcessingService:
    """Serviço de processamento de áudio baseado no classificador central."""

    @staticmethod
    def _normalize_result(raw_result: Dict) -> Dict:
        """Normaliza a saída do classificador para o formato usado pela API."""
        if not raw_result or not raw_result.get("sucesso", False):
            return {
                'success': False,
                'error': (raw_result or {}).get('erro', 'Erro desconhecido ao processar áudio'),
                'chords': [],
            }

        chords = []
        for acorde in raw_result.get('acordes', []):
            chords.append({
                'acorde': acorde.get('acorde'),
                'tempo_inicio': acorde.get('tempo_inicio') or acorde.get('inicio'),
                'duracao': acorde.get('duracao'),
                'confianca': acorde.get('confianca'),
            })

        metadata = {
            'duracao_total': raw_result.get('duracao_total'),
            'taxa_amostragem': raw_result.get('taxa_amostragem'),
            'total_acordes': raw_result.get('quantidade_acordes'),
        }

        return {
            'success': True,
            'chords': chords,
            'metadata': metadata,
        }

    @staticmethod
    def processar_audio(file_path: str) -> Dict:
        """Processa um arquivo local com o classificador central."""
        try:
            # Usa beat tracking por padrão (mais rápido)
            raw_result = chord_classifier.processar_audio(file_path, visualizar=False, metodo='beat')
            return AudioProcessingService._normalize_result(raw_result)
        except Exception as exc:
            logger.error(f"Erro ao processar arquivo local: {exc}")
            return {
                'success': False,
                'error': str(exc),
                'chords': [],
            }

    @staticmethod
    def processar_audio_url(file_url: str) -> Dict:
        """Baixa um arquivo remoto e processa com o classificador central."""
        tmp_path = None
        try:
            logger.info(f"Baixando áudio remoto para processamento: {file_url}")
            response = requests.get(file_url, timeout=60)
            response.raise_for_status()

            suffix = os.path.splitext(file_url)[1] or '.mp3'
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            return AudioProcessingService.processar_audio(tmp_path)
        except Exception as exc:
            logger.error(f"Erro ao processar URL: {exc}")
            return {
                'success': False,
                'error': str(exc),
                'chords': [],
            }
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)


# Atalhos

def processar_audio(file_path: str) -> Dict:
    return AudioProcessingService.processar_audio(file_path)


def processar_audio_url(file_url: str) -> Dict:
    return AudioProcessingService.processar_audio_url(file_url)
